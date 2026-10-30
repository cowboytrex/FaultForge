
import time
import uuid

from flask import g, request
from structured_logger import logger


def register_request_tracking(app):
    """Register request tracking hooks."""

    @app.before_request
    def start_request():
        g.request_id = str(uuid.uuid4())
        g.request_start_time = time.perf_counter()

        logger.info(
            "Request started",
            extra={
                "request_id": g.request_id,
                "method": request.method,
                "path": request.path,
            },
        )

    @app.after_request
    def finish_request(response):
        request_id = getattr(g, "request_id", None)
        start_time = getattr(g, "request_start_time", None)

        if request_id:
            response.headers["X-Request-ID"] = request_id

            duration_ms = (
                round((time.perf_counter() - start_time) * 1000, 2)
                if start_time is not None
                else None
            )

            logger.info(
                "Request completed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.path,
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                },
            )

        return response
