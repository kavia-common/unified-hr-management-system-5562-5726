from typing import Dict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette import status

from src.api.db import Base, engine, verify_database_connectivity
from src.api import models  # noqa: F401  # Ensure models are registered with Base for metadata

# Initialize FastAPI app with OpenAPI metadata and tags
app = FastAPI(
    title="HRMS Backend API",
    description=(
        "Unified HR Management System backend service. "
        "Provides RESTful endpoints, RBAC, and integrates with SQLite database."
    ),
    version="0.1.0",
    openapi_tags=[
        {"name": "Health", "description": "Service health and readiness checks"},
    ],
)

# Configure CORS (adjust allow_origins via env in future if needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    """
    FastAPI startup event to initialize the database schema.

    - Creates all tables defined on SQLAlchemy Base metadata if not present.
    - This ensures SQLite file/db is created on first run.
    """
    # Create tables if they do not exist.
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as exc:
        # Fail fast with clear error; container orchestration will restart based on policy.
        raise RuntimeError(f"Database initialization failed: {exc}") from exc


# PUBLIC_INTERFACE
@app.get("/", tags=["Health"], summary="Health Check", description="Returns 200 if the service is running.")
def health_check() -> Dict[str, str]:
    """
    Health check endpoint for liveness probes.

    Returns:
        Dict[str, str]: Simple status message.
    """
    return {"message": "Healthy"}


# PUBLIC_INTERFACE
@app.get(
    "/readiness",
    tags=["Health"],
    summary="Readiness Check",
    description="Verifies database connectivity and returns 200 if ready.",
    status_code=status.HTTP_200_OK,
)
def readiness_check() -> Dict[str, str]:
    """
    Readiness probe that validates DB connectivity.

    Returns:
        Dict[str, str]: Status message indicating readiness.
    """
    is_db_ok = verify_database_connectivity()
    if not is_db_ok:
        # Return 503 to indicate not ready; Starlette/FastAPI will handle status code via exception
        from fastapi import HTTPException

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database not ready",
        )
    return {"status": "ready"}
