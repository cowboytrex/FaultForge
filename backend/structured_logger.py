
import json
import logging
import sys

from datetime import datetime, timezone


class JSONFormatter(logging.Formatter):
    """Format application logs as structured JSON."""

    def format(self, record):
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage()
        }

        if hasattr(record, "event_type"):
            log_data["event_type"] = record.event_type

        for field in (
            "request_id",
            "method",
            "path",
            "status_code",
            "duration_ms",
        ):
            if hasattr(record, field):
                log_data[field] = getattr(record, field)
                
        if record.exc_info:
            log_data["exception"] = self.formatException(
                record.exc_info
            )

        return json.dumps(log_data)


def configure_logger():
    """Create a logger that outputs JSON to the terminal."""
    logger = logging.getLogger("faultforge")
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)

    logger.propagate = False

    return logger


logger = configure_logger()
