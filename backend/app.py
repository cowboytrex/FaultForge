import psycopg
from flask import Flask, jsonify, request
from redis.exceptions import RedisError
from database import get_services_from_db
from fallback import save_to_cache, get_cached_services

app = Flask(__name__)


@app.route("/")
def home():
    return jsonify({
        "project": "FaultForge",
        "message": "API is running successfully"
    })




@app.route("/api/services")
def services():
    simulate_failure = request.args.get("fail") == "true"

    try:
        if simulate_failure:
            raise ConnectionError("Simulated database failure")

        data = get_services_from_db()

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

    except (ConnectionError, psycopg.OperationalError):

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



if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)