"""
Database configuration and initialization for the HRMS backend.

This module:
- Loads environment variables for database URL/path (with secure defaults).
- Constructs a proper SQLite SQLAlchemy URL (file-based).
- Ensures the database directory exists for file-based SQLite.
- Exposes a SQLAlchemy engine, session factory, and Base for models.
- Provides a function to validate connectivity for health/readiness checks.

Security considerations:
- No secrets are hardcoded; configuration is via environment variables.
- SQLite is file-based and local to the backend container; access is controlled by file permissions.
- Input validation is performed for environment variable values.

TODO:
- If migrating to other databases later, update URL parsing/driver and add connection pooling accordingly.
"""

import os

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import declarative_base, sessionmaker

# Constants and configuration
DEFAULT_SQLITE_FILENAME = "hrms.db"
# Allow overriding via DATABASE_URL or SQLITE_DB_PATH. If neither provided, fallback to sqlite file in project dir.


def _get_database_url() -> str:
    """
    Resolve the database URL using env vars with safe defaults.

    Order:
    - DATABASE_URL (full SQLAlchemy URL)
    - SQLITE_DB_PATH (file path), converted to sqlite:///...
    - Default to sqlite:///./hrms.db

    Returns:
        str: A valid SQLAlchemy database URL.
    """
    database_url = os.getenv("DATABASE_URL")
    sqlite_path = os.getenv("SQLITE_DB_PATH")
    if database_url:
        return database_url.strip()

    # Validate sqlite_path if provided and convert to sqlite URL
    if sqlite_path:
        candidate = sqlite_path.strip()
        # Reject empty or whitespace-only
        if not candidate:
            # Will fallback below
            pass
        else:
            # Expand user and make absolute/relative safe path
            candidate = os.path.expanduser(candidate)
            # Construct sqlite URL with three slashes for relative, four for absolute
            if os.path.isabs(candidate):
                return f"sqlite:///{candidate}"
            return f"sqlite:///./{candidate}"

    # Default fallback: local file
    return f"sqlite:///./{DEFAULT_SQLITE_FILENAME}"


def _ensure_sqlite_dir_exists(database_url: str) -> None:
    """
    Ensure the directory for the SQLite database file exists.
    Only applies for sqlite file URLs (not memory or non-sqlite databases).

    Args:
        database_url (str): SQLAlchemy DB URL.
    """
    if not database_url.startswith("sqlite:///"):
        # Not a file-based sqlite URL; nothing to ensure
        return
    # Strip scheme
    path_part = database_url.replace("sqlite:///", "", 1)
    # In-memory db has special path ':memory:'
    if path_part == ":memory:":
        return
    # If relative path, interpret relative to CWD
    db_path = os.path.abspath(path_part)
    db_dir = os.path.dirname(db_path)
    try:
        os.makedirs(db_dir, exist_ok=True)
    except OSError as exc:
        # Raising is appropriate to fail fast on permission or filesystem issues
        raise RuntimeError(f"Failed to create database directory '{db_dir}': {exc}") from exc


DATABASE_URL: str = _get_database_url()
_ensure_sqlite_dir_exists(DATABASE_URL)

# Create SQLAlchemy engine; check_same_thread set to False for FastAPI multi-threaded access with SQLite
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
    pool_pre_ping=True,  # Helps detect dropped connections
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base declarative for models
Base = declarative_base()


# PUBLIC_INTERFACE
def get_db_session():
    """Provide a transactional scope around a series of operations (FastAPI dependency)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# PUBLIC_INTERFACE
def verify_database_connectivity() -> bool:
    """
    Check database connectivity by executing a trivial query.

    Returns:
        bool: True if query succeeds, otherwise False.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except SQLAlchemyError:
        return False
