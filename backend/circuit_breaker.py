
import time
import psycopg

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

            self.state = "HALF_OPEN"

        try:
            result = operation()

        except (ConnectionError, psycopg.OperationalError):
            self.failure_count += 1
            self.last_failure_time = time.monotonic()

            if (
                self.state == "HALF_OPEN"
                or self.failure_count >= self.failure_threshold
            ):
                self.state = "OPEN"

            raise

        else:
            self.failure_count = 0
            self.state = "CLOSED"
            self.last_failure_time = None
            return result
