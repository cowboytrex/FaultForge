from flask import Flask, jsonify, request
from data_source import get_services
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
        data = get_services(
            database_available=not simulate_failure
        )

        save_to_cache(data)

        return jsonify({
            "data": data,
            "source": "primary",
            "stale": False,
            "system_status": "healthy"
        }), 200

    except ConnectionError:
        cached_data = get_cached_services()

        if cached_data is not None:
            return jsonify({
                "data": cached_data,
                "source": "cache",
                "stale": True,
                "system_status": "degraded"
            }), 200

        return jsonify({
            "error": "Database unavailable and no cached data exists",
            "system_status": "unavailable"
        }), 503


if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)