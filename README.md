
# FaultForge

A fault-tolerant REST API with automated recovery, monitoring, and CI/CD.

FaultForge is a reliability engineering project built with Python and Flask. It demonstrates how backend systems respond to simulated failures using fault injection, circuit breakers, recovery mechanisms, and monitoring.

## Features

- REST API built with Flask
- PostgreSQL and Redis integration
- Database fault injection and recovery testing
- Circuit breaker pattern
- Chaos engineering experiments
- API latency monitoring and P95 metrics
- Performance alerts and persistent alert history
- Reliability monitoring dashboard
- Health-check endpoints
- Automated testing and GitHub Actions CI

## Technology Stack

- Python 3.12
- Flask
- PostgreSQL 16
- Redis 7
- SQLite (persistent alert history)
- Docker Compose
- pytest and pytest-cov
- GitHub Actions

## Prerequisites

Install the following before running FaultForge:

- Python 3.12
- Docker Desktop
- Git

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/cowboytrex/FaultForge.git
cd FaultForge
```

### 2. Create a virtual environment

```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
python -m pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and replace the example PostgreSQL password with a local development password.

Never commit `.env` to Git.

### 5. Start PostgreSQL and Redis

```bash
docker compose up -d
docker compose ps
```

Wait until both services report `healthy`.

### 6. Start the Flask application

```bash
PYTHONPATH=backend:. python -m flask --app backend.app run --port 5000
```

### 7. Open the monitoring dashboard

Visit:

http://127.0.0.1:5000/dashboard

## Health Checks

Application liveness:

```bash
curl http://127.0.0.1:5000/health/live
```

Alert storage health:

```bash
curl http://127.0.0.1:5000/api/health/alert-storage
```

The alert storage endpoint returns HTTP 503 if its health check fails.

## Running Tests

Run the unit test suite:

```bash
PYTHONPATH=backend:. python -m pytest -q -m "not integration"
```

Run tests with coverage:

```bash
PYTHONPATH=backend:. python -m pytest -q -m "not integration" --cov=backend --cov-report=term-missing --cov-fail-under=85
```

## Stop Services

Stop Flask with Ctrl+C in its terminal.

Stop PostgreSQL and Redis:

```bash
docker compose down
```

This preserves the PostgreSQL Docker volume.

## Development and Deployment Notes

- Docker Compose currently runs PostgreSQL and Redis.
- The Flask application runs locally in a Python virtual environment.
- SQLite stores persistent performance alert history in `data/alerts.db`.
- Local environment variables are stored in `.env`, which is excluded from Git.
- Flask's development server is not intended for production deployment.
- This repository is a reliability engineering demonstration, not a production-hosted service.

## License

See [LICENSE](LICENSE).
