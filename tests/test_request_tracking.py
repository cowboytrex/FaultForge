
import sys
import uuid
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
