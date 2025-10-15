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

import logging
import os

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import declarative_base, sessionmaker

# Configure module-level logger
logger = logging.getLogger(__name__)

# Constants and configuration
DEFAULT_SQLITE_FILENAME = "hrms.db"
# Allow overriding via DATABASE_URL or SQLITE_DB_PATH. If neither provided, fallback to sqlite file in project dir.


def _get_database_url() -> str:
    """
    Resolve the database URL using env vars with safe defaults.

    Order:
    - DATABASE_URL (full SQLAlchemy URL)
    - SQLITE_DB_PATH (file path), converted to sqlite:///...
    - As compatibility fallback, REACT_APP_DATABASE_URL or REACT_APP_SQLITE_DB_PATH (if present)
    - Default to sqlite:///./hrms.db

    Returns:
        str: A valid SQLAlchemy database URL.
    """
    # Primary backend-scoped variables
    database_url = os.getenv("DATABASE_URL") or os.getenv("REACT_APP_DATABASE_URL")
    sqlite_path = os.getenv("SQLITE_DB_PATH") or os.getenv("REACT_APP_SQLITE_DB_PATH")

    if database_url:
        url = database_url.strip()
        if not url:
            logger.warning("DATABASE_URL provided but empty; continuing to next fallback")
        else:
            # Log only the scheme to avoid exposing local paths in some deployments
            logger.info(
                "Using database URL with scheme: %s",
                url.split(":", 1)[0] if ":" in url else "unknown",
            )
            return url

    # Validate sqlite_path if provided and convert to sqlite URL
    if sqlite_path:
        candidate = sqlite_path.strip()
        # Reject empty or whitespace-only
        if not candidate:
            logger.warning("SQLITE_DB_PATH provided but empty; continuing to default")
        else:
            # Expand user and make absolute/relative safe path
            candidate = os.path.expanduser(candidate)
            # Construct sqlite URL with three slashes for relative, four for absolute
            if os.path.isabs(candidate):
                url = f"sqlite:///{candidate}"
            else:
                url = f"sqlite:///./{candidate}"
            logger.info("Resolved SQLITE_DB_PATH to sqlite URL")
            return url

    # Default fallback: local file
    url = f"sqlite:///./{DEFAULT_SQLITE_FILENAME}"
    logger.info("Falling back to default sqlite URL at project directory")
    return url


def _sqlite_file_path_from_url(database_url: str) -> str | None:
    """
    Extract the filesystem path for a sqlite file URL.

    Args:
        database_url: The SQLAlchemy database URL.

    Returns:
        str | None: Absolute file path if sqlite file-based; otherwise None.
    """
    if not database_url.startswith("sqlite:///"):
        return None
    path_part = database_url.replace("sqlite:///", "", 1)
    if path_part == ":memory:":
        return None
    return os.path.abspath(path_part)


def _ensure_sqlite_dir_exists(database_url: str) -> None:
    """
    Ensure the directory for the SQLite database file exists.
    Only applies for sqlite file URLs (not memory or non-sqlite databases).

    Args:
        database_url (str): SQLAlchemy DB URL.
    """
    db_path = _sqlite_file_path_from_url(database_url)
    if not db_path:
        # Not applicable (non-sqlite file or memory)
        return
    db_dir = os.path.dirname(db_path)
    try:
        os.makedirs(db_dir, exist_ok=True)
        # Basic sanity: directory should be writable
        if not os.access(db_dir, os.W_OK):
            raise PermissionError(f"Directory '{db_dir}' is not writable")
    except OSError as exc:
        # Raising is appropriate to fail fast on permission or filesystem issues
        raise RuntimeError(f"Failed to create or access database directory '{db_dir}': {exc}") from exc


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

# Log limited DB diagnostics (non-sensitive) to aid startup issues
try:
    scheme = DATABASE_URL.split(":", 1)[0] if ":" in DATABASE_URL else "unknown"
    if scheme == "sqlite":
        db_path = os.path.abspath(DATABASE_URL.replace("sqlite:///", "", 1)) if DATABASE_URL.startswith("sqlite:///") else ""
        logger.info("DB init: scheme=%s sqlite_path=%s", scheme, db_path if db_path else "(not a file path)")
    else:
        logger.info("DB init: scheme=%s", scheme)
except Exception:  # pragma: no cover - defensive
    logger.debug("DB init diagnostics logging skipped due to unexpected error")


# PUBLIC_INTERFACE
def get_db_session():
    """Provide a transactional scope around a series of operations (FastAPI dependency)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _check_sqlite_file_permissions(db_path: str) -> tuple[bool, str]:
    """
    Perform simple permission checks on sqlite file/parent directory.

    Returns:
        tuple[bool, str]: (is_ok, details)
    """
    try:
        # Parent directory must exist and be writable (checked earlier)
        # If file exists, ensure read/write; if not, parent write is sufficient
        if os.path.exists(db_path):
            mode = os.stat(db_path).st_mode
            readable = os.access(db_path, os.R_OK)
            writable = os.access(db_path, os.W_OK)
            if not (readable and writable):
                return False, f"SQLite file at '{db_path}' not readable/writable (mode={oct(mode)})"
        else:
            # Attempt a harmless touch via open/close to validate permissions; do not keep file if it fails later
            try:
                with open(db_path, "a", encoding="utf-8"):
                    pass
            except OSError as exc:
                return False, f"Cannot create SQLite file at '{db_path}': {exc}"
        return True, "OK"
    except Exception as exc:  # pragma: no cover - defensive
        return False, f"Unexpected error checking sqlite file permissions: {exc}"


# PUBLIC_INTERFACE
def verify_database_connectivity() -> bool:
    """
    Check database connectivity by executing a trivial query.
    For sqlite file-based URLs, also validate that the file path is usable.

    Returns:
        bool: True if query and (if applicable) file checks succeed, otherwise False.
    """
    try:
        # Extra checks for sqlite file-based path
        db_path = _sqlite_file_path_from_url(DATABASE_URL)
        if db_path:
            ok, reason = _check_sqlite_file_permissions(db_path)
            if not ok:
                logger.error("SQLite file permission check failed: %s", reason)
                return False

        # Connectivity check
        with engine.connect() as conn:
            # Using pragma quick_check for sqlite if applicable, else SELECT 1
            if DATABASE_URL.startswith("sqlite"):
                conn.execute(text("PRAGMA quick_check"))
            else:
                conn.execute(text("SELECT 1"))
        return True
    except SQLAlchemyError as exc:
        logger.error("Database connectivity check failed: %s", exc)
        return False
    except Exception as exc:  # pragma: no cover - defensive
        logger.error("Unexpected error during DB readiness check: %s", exc)
        return False


# PUBLIC_INTERFACE
def get_database_info() -> dict:
    """
    Provide limited diagnostic info about the configured database.
    Note: does not expose sensitive data.

    Returns:
        dict: Diagnostic details useful for logs or admin-only endpoints.
    """
    info: dict = {
        "url_scheme": DATABASE_URL.split(":", 1)[0] if ":" in DATABASE_URL else "unknown",
        "is_sqlite": DATABASE_URL.startswith("sqlite"),
    }
    db_path = _sqlite_file_path_from_url(DATABASE_URL)
    if db_path:
        info.update(
            {
                "sqlite_path": db_path,
                "sqlite_dir_exists": os.path.isdir(os.path.dirname(db_path)),
                "sqlite_file_exists": os.path.isfile(db_path),
            }
        )
    return info
