
import os


class Config:
    """Central configuration for FaultForge."""

    # Flask configuration
    DEBUG = False
    TESTING = False

    # Fault injection is disabled by default.
    ENABLE_FAULT_INJECTION = False

    @classmethod
    def from_environment(cls):
        """Load configuration from environment variables."""
        return {
            "DEBUG": os.getenv("FLASK_DEBUG", "false").lower() == "true",
            "ENABLE_FAULT_INJECTION": (
                os.getenv("ENABLE_FAULT_INJECTION", "false").lower()
                == "true"
            ),
        }

    @classmethod
    def from_environment(cls):
        """Load configuration from environment variables."""
        return {
            "DEBUG": os.getenv("FLASK_DEBUG", "false").lower() == "true",
            "ENABLE_FAULT_INJECTION": (
                os.getenv("ENABLE_FAULT_INJECTION", "false").lower()
                == "true"
            ),
            "CHAOS_API_ENABLED": (
                os.getenv("CHAOS_API_ENABLED", "false").lower()
                == "true"
            ),
        }