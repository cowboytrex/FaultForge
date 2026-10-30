
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "backend")
)

import database


def test_get_services_success(monkeypatch):
    """Database query should return service records."""

    expected_services = [
        {"id": 1, "name": "API", "status": "healthy"},
        {"id": 2, "name": "Redis", "status": "healthy"},
    ]

    mock_connection = MagicMock()
    mock_cursor = MagicMock()

    mock_connection.cursor.return_value.__enter__.return_value = (
        mock_cursor
    )
    mock_cursor.fetchall.return_value = expected_services

    mock_connect = MagicMock(return_value=mock_connection)

    monkeypatch.setenv("DB_PASSWORD", "test_password")
    monkeypatch.setattr(
        database.psycopg,
        "connect",
        mock_connect,
    )

    result = database.get_services_from_db()

    assert result == expected_services

    mock_cursor.execute.assert_called_once_with(
        "SELECT id, name, status FROM services ORDER BY id"
    )

    mock_connection.close.assert_called_once()


def test_database_connection_failure(monkeypatch):
    """Connection failures should propagate to the caller."""

    def failing_connect(**kwargs):
        raise ConnectionError("PostgreSQL unavailable")

    monkeypatch.setenv("DB_PASSWORD", "test_password")
    monkeypatch.setattr(
        database.psycopg,
        "connect",
        failing_connect,
    )

    with pytest.raises(
        ConnectionError,
        match="PostgreSQL unavailable",
    ):
        database.get_services_from_db()


def test_database_query_failure_closes_connection(monkeypatch):
    """Connection should close even if the query fails."""

    mock_connection = MagicMock()
    mock_cursor = MagicMock()

    mock_connection.cursor.return_value.__enter__.return_value = (
        mock_cursor
    )

    mock_cursor.execute.side_effect = RuntimeError(
        "Database query failed"
    )

    monkeypatch.setenv("DB_PASSWORD", "test_password")
    monkeypatch.setattr(
        database.psycopg,
        "connect",
        lambda **kwargs: mock_connection,
    )

    with pytest.raises(
        RuntimeError,
        match="Database query failed",
    ):
        database.get_services_from_db()

    mock_connection.close.assert_called_once()


def test_database_connection_configuration(monkeypatch):
    """Database connection should use configured environment values."""

    mock_connection = MagicMock()
    mock_cursor = MagicMock()

    mock_connection.cursor.return_value.__enter__.return_value = (
        mock_cursor
    )
    mock_cursor.fetchall.return_value = []

    mock_connect = MagicMock(return_value=mock_connection)

    monkeypatch.setenv("DB_HOST", "test-db")
    monkeypatch.setenv("DB_PORT", "5434")
    monkeypatch.setenv("DB_NAME", "test_faultforge")
    monkeypatch.setenv("DB_USER", "test_user")
    monkeypatch.setenv("DB_PASSWORD", "test_password")

    monkeypatch.setattr(
        database.psycopg,
        "connect",
        mock_connect,
    )

    database.get_services_from_db()

    connection_args = mock_connect.call_args.kwargs

    assert connection_args["host"] == "test-db"
    assert connection_args["port"] == 5434
    assert connection_args["dbname"] == "test_faultforge"
    assert connection_args["user"] == "test_user"
    assert connection_args["password"] == "test_password"
    assert connection_args["connect_timeout"] == 3
