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
from dependency_monitor import check_dependencies
from chaos_engine import chaos_engine
from latency_collector import latency_collector
from backend.experiment_store import load_experiments
from backend.alert_history import alert_history
from backend.performance_alerts import evaluate_latency_alert


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

@app.route("/api/metrics")
def metrics():
    return jsonify(calculate_metrics())


@app.route("/api/metrics/trends")
def metrics_trends():
    return jsonify({
        "trends": calculate_daily_trends()
    })


@app.route("/api/metrics/latency")
def latency_metrics_api():
    """Return performance metrics for recent HTTP requests."""
    return jsonify(latency_collector.metrics())


@app.route("/api/metrics/latency/history")
def latency_history_api():
    """Return timestamped HTTP request latency samples."""
    history = latency_collector.history()

    return jsonify({
        "total": len(history),
        "history": history,
    })



@app.route("/api/metrics/latency/alert")
def latency_alert_api():
    """Return current latency status and record status changes."""
    metrics = latency_collector.metrics()

    if metrics["total_requests"] == 0:
        result = {
            "status": "no_data",
            "message": "No latency measurements available",
            "p95_latency_ms": None,
            "warning_threshold_ms": 200,
            "critical_threshold_ms": 500,
        }
    else:
        result = evaluate_latency_alert(
            p95_latency_ms=metrics["p95_latency_ms"],
            warning_threshold_ms=200,
            critical_threshold_ms=500,
        )

    # Record only when the alert status changes.
    alert_history.record(
        status=result["status"],
        p95_latency_ms=result["p95_latency_ms"],
    )

    return jsonify(result)


@app.route("/api/metrics/latency/alerts/history")
def latency_alert_history_api():
    """Return recorded performance alert transitions."""
    events = alert_history.history()

    return jsonify({
        "total": len(events),
        "history": events,
    })


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

        if app.config["ENABLE_FAULT_INJECTION"]:
            data = db_breaker.call(
                lambda: chaos_engine.execute(database_operation)
            )
        else:
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


@app.route("/api/chaos/reset", methods=["POST"])
def reset_chaos():
    """Disable active chaos experiments."""

    if not (
        app.config.get("ENABLE_FAULT_INJECTION", False)
        and app.config.get("CHAOS_API_ENABLED", False)
    ):
        return jsonify({
            "error": "Chaos configuration API is disabled"
        }), 403

    if request.remote_addr not in ("127.0.0.1", "::1"):
        return jsonify({
            "error": "Chaos reset is restricted to localhost"
        }), 403

    chaos_engine.configure(
        enabled=False,
        latency_ms=0,
        failure_rate=0.0,
    )

    return jsonify({
        "message": "Chaos experiments disabled",
        "enabled": False,
        "latency_ms": 0,
        "failure_rate": 0.0,
    }), 200


@app.route("/api/chaos/configure", methods=["POST"])
def configure_chaos():
    """Configure controlled chaos experiments in local development."""

    if not (
        app.config.get("ENABLE_FAULT_INJECTION", False)
        and app.config.get("CHAOS_API_ENABLED", False)
    ):
        return jsonify({
            "error": "Chaos configuration API is disabled"
        }), 403

    # This endpoint is intended for local development only.
    if request.remote_addr not in ("127.0.0.1", "::1"):
        return jsonify({
            "error": "Chaos configuration is restricted to localhost"
        }), 403

    payload = request.get_json(silent=True)

    if not isinstance(payload, dict):
        return jsonify({
            "error": "A JSON object is required"
        }), 400

    enabled = payload.get("enabled", False)
    latency_ms = payload.get("latency_ms", 0)
    failure_rate = payload.get("failure_rate", 0.0)

    if not isinstance(enabled, bool):
        return jsonify({
            "error": "enabled must be a boolean"
        }), 400

    # Reject booleans, which Python otherwise treats as numbers.
    if (
        type(latency_ms) not in (int, float)
        or type(failure_rate) not in (int, float)
    ):
        return jsonify({
            "error": "latency_ms and failure_rate must be numeric"
        }), 400

    try:
        chaos_engine.configure(
            enabled=enabled,
            latency_ms=latency_ms,
            failure_rate=failure_rate,
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    return jsonify({
        "message": "Chaos configuration updated",
        "enabled": chaos_engine.enabled,
        "latency_ms": chaos_engine.latency_ms,
        "failure_rate": chaos_engine.failure_rate,
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
    """Check readiness without modifying circuit-breaker state."""

    def database_check():
        get_services_from_db()
        return True

    def cache_check():
        return get_cached_services() is not None

    result, status_code = check_dependencies(
        database_check=database_check,
        cache_check=cache_check,
    )

    return jsonify(result), status_code


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


@app.route("/api/chaos/experiments", methods=["GET"])
def get_chaos_experiments():
    """Return saved chaos engineering experiments."""
    try:
        experiments = load_experiments()

        return jsonify({
            "total": len(experiments),
            "experiments": experiments,
        }), 200

    except (OSError, ValueError) as error:
        app.logger.error(
            "Failed to load experiment history: %s",
            error,
        )

        return jsonify({
            "error": "Unable to load experiment history"
        }), 500

