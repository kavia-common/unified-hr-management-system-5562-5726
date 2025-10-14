"""
SQLAlchemy models for HRMS.

This file defines minimal initial models so that the database can be initialized on startup.
For production features, extend with real domain models (employees, users, roles, etc.).

Security considerations:
- Use SQLAlchemy to avoid SQL injection via parameterized queries.
- Add appropriate constraints and indices as domain grows.

TODO:
- Replace ExampleModel with actual domain models.
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String

from src.api.db import Base


class ExampleModel(Base):
    """
    Minimal example model used to verify migrations/initialization and DB connectivity.
    Replace with real models as features are implemented.
    """

    __tablename__ = "example_items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
