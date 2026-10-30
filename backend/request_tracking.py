
import uuid

from flask import g, request
from structured_logger import logger


def register_request_tracking(app):
    """Register request tracking hooks."""

    @app.before_request
    def start_request():
        g.request_id = str(uuid.uuid4())

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

        if request_id:
            response.headers["X-Request-ID"] = request_id

            logger.info(
                "Request completed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.path,
                    "status_code": response.status_code,
                },
            )

        return response
