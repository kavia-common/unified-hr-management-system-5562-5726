# HRMS Backend (FastAPI)

This service provides the REST API for the Unified HR Management System.

## Run locally

- Install dependencies:
  pip install -r requirements.txt

- Start the server (binds to 0.0.0.0:3001 by default):
  python run.py

Alternative (explicit ASGI module):
  uvicorn hrms_backend.asgi:app --host 0.0.0.0 --port 3001

You can override host/port via env:
- HOST=0.0.0.0
- PORT=3001
- LOG_LEVEL=info

## Health and readiness

- Liveness: GET /
- Readiness: GET /readiness (validates database connectivity)

## Configuration

The service reads database configuration from environment variables:

Priority order:
1. DATABASE_URL (e.g., sqlite:///./data/hrms.db)
2. SQLITE_DB_PATH (e.g., ./data/hrms.db)
3. REACT_APP_DATABASE_URL
4. REACT_APP_SQLITE_DB_PATH
5. Default sqlite:///./hrms.db

See .env.example for details.
