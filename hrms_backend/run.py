"""
Application entrypoint to start the FastAPI app with uvicorn.

This script ensures the app binds to the correct host and port for containerized
environments and provides basic structured logging.

Environment variables:
- HOST: Interface to bind to. Default "0.0.0.0" for containers.
- PORT: Port to listen on. Default 3001 to match container expectations.
- LOG_LEVEL: Uvicorn log level. Default "info".

Security considerations:
- Do not log sensitive environment variables.
- Host/port are safe to log.

Usage:
    python run.py
    or
    uvicorn src.api.main:app --host 0.0.0.0 --port 3001
    or
    uvicorn hrms_backend.asgi:app --host 0.0.0.0 --port 3001
"""

import logging
import os
from typing import Any

import uvicorn

# PUBLIC_INTERFACE
def get_server_config() -> dict[str, Any]:
    """Return host/port/logging configuration derived from environment variables."""
    # Validate and coerce PORT to int with safe fallback
    raw_port = os.getenv("PORT", "3001")
    try:
        port = int(raw_port)
        if not (1 <= port <= 65535):
            raise ValueError("port out of range")
    except Exception:
        port = 3001

    host = os.getenv("HOST", "0.0.0.0")
    # Prevent accidental binding to localhost only in containerized envs
    if host.strip() == "":
        host = "0.0.0.0"

    log_level = os.getenv("LOG_LEVEL", "info").lower()
    return {"host": host, "port": port, "log_level": log_level}


def main() -> None:
    """Start the ASGI server for the FastAPI app."""
    cfg = get_server_config()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )
    logging.getLogger(__name__).info("Starting HRMS backend on %s:%s", cfg["host"], cfg["port"])

    # Use app path as module: "src.api.main:app"
    uvicorn.run(
        "src.api.main:app",
        host=cfg["host"],
        port=cfg["port"],
        log_level=cfg["log_level"],
        workers=1,  # Single worker to simplify SQLite access; scale with proper DB later
    )


if __name__ == "__main__":
    main()
