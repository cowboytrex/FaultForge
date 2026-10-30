
import time
import psycopg

from event_logger import log_event


class CircuitOpenError(Exception):
    """Raised when the circuit breaker blocks a request."""


class CircuitBreaker:
    def __init__(self, failure_threshold=3, recovery_timeout=10):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.state = "CLOSED"
        self.last_failure_time = None

    def call(self, operation):
        """Execute an operation if the circuit permits it."""

        if self.state == "OPEN":
            elapsed = time.monotonic() - self.last_failure_time

            if elapsed < self.recovery_timeout:
                raise CircuitOpenError("Circuit breaker is OPEN")

            # Recovery timeout expired: allow a trial request.
            self.state = "HALF_OPEN"

            log_event(
                "recovery_attempt",
                "Circuit breaker entered HALF_OPEN. Testing database recovery.",
                "info"
            )

        try:
            result = operation()

        except (ConnectionError, psycopg.OperationalError):
            self.failure_count += 1
            self.last_failure_time = time.monotonic()

            log_event(
                "database_failure",
                f"Database request failed. Failure count: {self.failure_count}.",
                "warning"
            )

            if (
                self.state == "HALF_OPEN"
                or self.failure_count >= self.failure_threshold
            ):
                if self.state != "OPEN":
                    self.state = "OPEN"

                    log_event(
                        "circuit_opened",
                        "Circuit breaker opened after database failures.",
                        "critical"
                    )

            raise

        else:
            previous_state = self.state

            self.failure_count = 0
            self.state = "CLOSED"
            self.last_failure_time = None

            if previous_state == "HALF_OPEN":
                log_event(
                    "database_recovered",
                    "Database recovery successful. Circuit breaker returned to CLOSED.",
                    "info"
                )

            return result
