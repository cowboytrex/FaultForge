import time
import psycopg
import os
from config import Config
from flask import Flask, jsonify, request, render_template
from redis.exceptions import RedisError
from database import get_services_from_db
from fallback import save_to_cache, get_cached_services
from circuit_breaker import CircuitBreaker, CircuitOpenError
from event_logger import log_event, get_events
from request_tracking import register_request_tracking
from metrics import calculate_metrics
from metrics import calculate_metrics, calculate_daily_trends


app = Flask(__name__)
app.config.update(Config.from_environment())

register_request_tracking(app)
db_breaker = CircuitBreaker(
    failure_threshold=3,
    recovery_timeout=10
)
@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")

@app.route("/api/metrics/trends")
def metrics_trends():
    return jsonify({
        "trends": calculate_daily_trends()
    })

@app.route("/api/metrics")
def metrics():
    return jsonify(calculate_metrics())

@app.route("/")
def home():
    return jsonify({
        "project": "FaultForge",
        "message": "API is running successfully"
    })

@app.route("/api/events")
def events_api():
    return jsonify({
        "events": get_events()
    })


@app.route("/api/services")
def get_services():
    simulate_failure = request.args.get("fail") == "true"

    if simulate_failure:
        if not app.config["ENABLE_FAULT_INJECTION"]:
            return jsonify({
                "error": "Fault injection is disabled"
            }), 403

    # Keep your existing database, Redis,
    # and circuit breaker logic below.

    try:
        def database_operation():
            if request.args.get("fail") == "true":
                raise ConnectionError("Simulated database failure")

            return get_services_from_db()
        
        data = db_breaker.call(database_operation)

        # A Redis failure should not prevent a healthy database response.
        try:
            save_to_cache(data)
            cache_status = "available"
        except RedisError:
            cache_status = "unavailable"

        return jsonify({
            "data": data,
            "source": "primary",
            "stale": False,
            "system_status": "healthy",
            "cache_status": cache_status
        }), 200

    except (ConnectionError, psycopg.OperationalError, CircuitOpenError):

        # PostgreSQL is unavailable; attempt Redis fallback.
        try:
            cached_data = get_cached_services()
        except RedisError:
            cached_data = None

        if cached_data is not None:
            return jsonify({
                "data": cached_data,
                "source": "cache",
                "stale": True,
                "system_status": "degraded",
                "cache_status": "available"
            }), 200

        return jsonify({
            "error": "Database unavailable and no cached data exists",
            "system_status": "unavailable",
            "cache_status": "unavailable_or_empty"
        }), 503


@app.route("/api/simulate-failure", methods=["POST"])
def simulate_failure():
    # Step 1: Check whether fault injection is enabled.
    if not app.config["ENABLE_FAULT_INJECTION"]:
        return jsonify({
            "error": "Fault injection is disabled"
        }), 403

    # Step 3: Simulate a database failure when enabled.
    with app.test_client() as client:
        response = client.get("/api/services?fail=true")

    # Step 4: Return the simulation results.
    return jsonify({
        "message": "Simulated database failure request completed",
        "request_status": response.status_code,
        "system_status": response.get_json().get("system_status"),
        "circuit_breaker": {
            "state": db_breaker.state,
            "failure_count": db_breaker.failure_count
        }
    }), 200


@app.route("/health/live", methods=["GET"])
def health_live():
    """Check whether the Flask application is running."""
    return jsonify({
        "status": "alive",
        "service": "faultforge"
    }), 200


@app.route("/health/ready", methods=["GET"])
def health_ready():
    """Check whether FaultForge can serve requests."""

    with app.test_client() as client:
        response = client.get("/api/services")

    if response.status_code != 200:
        return jsonify({
            "status": "not_ready",
            "reason": "Service check failed"
        }), 503

    data = response.get_json() or {}
    system_status = data.get("system_status")

    if system_status == "healthy":
        return jsonify({
            "status": "ready",
            "system_status": "healthy"
        }), 200

    if system_status == "degraded":
        return jsonify({
            "status": "ready",
            "system_status": "degraded"
        }), 200

    return jsonify({
        "status": "not_ready",
        "system_status": system_status or "unknown"
    }), 503

@app.route("/api/monitoring")
def monitoring():
    recovery_remaining = 0

    if (
        db_breaker.state == "OPEN"
        and db_breaker.last_failure_time is not None
    ):
        elapsed = time.monotonic() - db_breaker.last_failure_time

        recovery_remaining = max(
            0,
            round(db_breaker.recovery_timeout - elapsed, 1)
        )

    return jsonify({
        "circuit_breaker": {
            "state": db_breaker.state,
            "failure_count": db_breaker.failure_count,
            "failure_threshold": db_breaker.failure_threshold,
            "recovery_timeout": db_breaker.recovery_timeout,
            "recovery_remaining": recovery_remaining
        }
    })

if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5001,
        debug=True,
        use_reloader=False
    )