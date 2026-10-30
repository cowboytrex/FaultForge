
import sys
import uuid
import json
import logging
from pathlib import Path

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "backend")
)

from flask import Flask
from request_tracking import register_request_tracking


def create_test_app():
    app = Flask(__name__)
    app.config["TESTING"] = True

    register_request_tracking(app)

    @app.route("/test")
    def test_endpoint():
        return {"message": "ok"}

    return app


def test_request_id_header_exists():
    app = create_test_app()

    with app.test_client() as client:
        response = client.get("/test")

    assert response.status_code == 200
    assert "X-Request-ID" in response.headers


def test_request_id_is_valid_uuid():
    app = create_test_app()

    with app.test_client() as client:
        response = client.get("/test")

    request_id = response.headers["X-Request-ID"]

    assert str(uuid.UUID(request_id)) == request_id


def test_each_request_has_unique_id():
    app = create_test_app()

    with app.test_client() as client:
        first = client.get("/test")
        second = client.get("/test")

    assert (
        first.headers["X-Request-ID"]
        != second.headers["X-Request-ID"]
    )


def test_completed_request_logs_latency_and_request_id(caplog):
    app = create_test_app()

    # FaultForge's logger normally disables propagation.
    # Enable it temporarily so pytest can capture log records.
    faultforge_logger = logging.getLogger("faultforge")
    original_propagate = faultforge_logger.propagate

    try:
        faultforge_logger.propagate = True

        with caplog.at_level(logging.INFO, logger="faultforge"):
            caplog.clear()

            with app.test_client() as client:
                response = client.get("/test")

        completed_records = [
            record
            for record in caplog.records
            if record.name == "faultforge"
            and record.getMessage() == "Request completed"
            and getattr(record, "request_id", None)
            == response.headers["X-Request-ID"]
        ]

                # Deduplicate records by object identity.
        # The same LogRecord may be captured through multiple handlers.
        unique_records = {
            id(record): record
            for record in completed_records
        }

        assert len(unique_records) == 1

        record = next(iter(unique_records.values()))

        assert record.request_id == response.headers["X-Request-ID"]
        assert record.method == "GET"
        assert record.path == "/test"
        assert record.status_code == 200

        assert isinstance(record.duration_ms, (int, float))
        assert record.duration_ms >= 0

        # Verify the production formatter includes latency in JSON.
        from structured_logger import JSONFormatter

        log_data = json.loads(JSONFormatter().format(record))

        assert log_data["duration_ms"] == record.duration_ms
        assert log_data["request_id"] == response.headers["X-Request-ID"]

    finally:
        faultforge_logger.propagate = original_propagate
