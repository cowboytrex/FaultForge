
import random
import time


class ChaosEngine:
    """Inject controlled faults into database operations."""

    def __init__(self):
        self.enabled = False
        self.latency_ms = 0
        self.failure_rate = 0.0

    def configure(self, enabled=False, latency_ms=0, failure_rate=0.0):
        """Configure the active fault injection scenario."""

        if not isinstance(latency_ms, (int, float)) or not 0 <= latency_ms <= 5000:
            raise ValueError("latency_ms must be between 0 and 5000")

        if not isinstance(failure_rate, (int, float)) or not 0 <= failure_rate <= 1:
            raise ValueError("failure_rate must be between 0 and 1")

        self.enabled = enabled
        self.latency_ms = latency_ms
        self.failure_rate = failure_rate

    def execute(self, operation):
        """Apply configured faults before running an operation."""

        if not self.enabled:
            return operation()

        if self.latency_ms > 0:
            time.sleep(self.latency_ms / 1000)

        if random.random() < self.failure_rate:
            raise ConnectionError("Chaos experiment: simulated database failure")

        return operation()


chaos_engine = ChaosEngine()
