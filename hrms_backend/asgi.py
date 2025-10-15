"""
ASGI entrypoint for the HRMS Backend.

This module ensures the project root is on sys.path so that "src.api.main:app"
resolves correctly regardless of current working directory. It also exposes
`app` for ASGI servers (uvicorn, hypercorn).

Usage examples:
- uvicorn hrms_backend.asgi:app --host 0.0.0.0 --port 3001
- python -m uvicorn hrms_backend.asgi:app --host 0.0.0.0 --port 3001
"""

import os
import sys

# Ensure project root is on sys.path to reliably import src.api.main
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import the FastAPI app
from src.api.main import app  # noqa: E402  (import after path adjustment)

# Make 'app' visible to tools and prevent linter from flagging as unused.
__all__ = ["app"]
