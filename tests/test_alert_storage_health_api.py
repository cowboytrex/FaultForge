
import importlib

app_module = importlib.import_module("backend.app")


def test_alert_storage_health_api_healthy(monkeypatch):
    """Healthy SQLite storage should return HTTP 200."""

    class HealthyRepository:
        def health_check(self):
            return True

    monkeypatch.setattr(
        app_module,
        "AlertRepository",
        HealthyRepository,
    )

    client = app_module.app.test_client()
    response = client.get("/api/health/alert-storage")

    assert response.status_code == 200
    assert response.get_json() == {
        "service": "alert_storage",
        "status": "healthy",
        "database": "sqlite",
    }


def test_alert_storage_health_api_unhealthy(monkeypatch):
    """Unavailable SQLite storage should return HTTP 503."""

    class UnhealthyRepository:
        def health_check(self):
            return False

    monkeypatch.setattr(
        app_module,
        "AlertRepository",
        UnhealthyRepository,
    )

    client = app_module.app.test_client()
    response = client.get("/api/health/alert-storage")

    assert response.status_code == 503
    assert response.get_json() == {
        "service": "alert_storage",
        "status": "unhealthy",
        "database": "sqlite",
    }


def test_alert_storage_health_api_handles_exception(monkeypatch):
    """Unexpected storage errors should return HTTP 503."""

    class FailingRepository:
        def health_check(self):
            raise OSError("Simulated database failure")

    monkeypatch.setattr(
        app_module,
        "AlertRepository",
        FailingRepository,
    )

    client = app_module.app.test_client()
    response = client.get("/api/health/alert-storage")

    assert response.status_code == 503
    assert response.get_json()["status"] == "unhealthy"

