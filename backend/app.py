from flask imort Flask, jsonify, request
from data_source import get_services

app = Flask(__name__)

@app.route("/")
def home():
    return jsonify({
        "project": "Faultforge",
        "message": "API is running successfully"
    })

@app.route("/api/services")
def services():
    simulate_failure = request.args.get("fail") == "true"

    try:
        data = get_services(
            database_available=not simulate_failure
        )

        return jsonify({
            "data": data,
            "source": "primary",
            "system_status": "healthy"
        }), 200

    except ConnectionError as error:
        return jsonify({
            "error": str(error),
            "system_status": "degraded"
        }), 503

if __name__ == "__main__":
    app.run(debug=True)