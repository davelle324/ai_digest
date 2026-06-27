"""
Shared test fixtures for AI Digest API.

Key guarantees:
- All tests use an in-memory SQLite database (no real data stored)
- RESEND_API_KEY is empty so no real emails are sent
- SUMMARIZER_ENABLED=false so no Ollama calls are made
- APScheduler is patched out (no background jobs in tests)
"""
import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Set all env vars BEFORE importing any app modules.
# app.db reads DATABASE_URL at import time, so this must come first.
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("ADMIN_SECRET", "test-admin-secret")
os.environ.setdefault("RESEND_API_KEY", "")  # empty = no real emails
os.environ.setdefault("RESEND_FROM", "test@test.com")
os.environ.setdefault("SITE_URL", "http://localhost:3000")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")
os.environ.setdefault("SUMMARIZER_ENABLED", "false")

from app.db import Base, get_db  # noqa: E402
from app.main import app, limiter  # noqa: E402

# Single shared in-memory engine for all tests.
# StaticPool ensures every connection hits the same in-memory database.
_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_Session = sessionmaker(autocommit=False, autoflush=False, bind=_engine)


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """Clear slowapi in-memory rate limit counters before each test."""
    # Access the underlying limits storage and reset all window counters.
    storage = getattr(getattr(limiter, "_limiter", None), "storage", None)
    if storage is not None and hasattr(storage, "reset"):
        storage.reset()
    yield


@pytest.fixture(scope="session", autouse=True)
def _create_tables():
    """Create all tables once per test session."""
    import app.models  # noqa: F401 — registers models with Base
    Base.metadata.create_all(bind=_engine)
    yield
    Base.metadata.drop_all(bind=_engine)


@pytest.fixture()
def db():
    """
    Yields a database session backed by the in-memory test database.
    All writes are rolled back and tables cleared after each test.
    """
    session = _Session()
    yield session
    session.rollback()
    for table in reversed(Base.metadata.sorted_tables):
        session.execute(table.delete())
    session.commit()
    session.close()


@pytest.fixture()
def client(db):
    """
    FastAPI TestClient with:
    - get_db overridden to use the test session
    - Scheduler patched out (no background jobs)
    - init_db patched out (tables already created by _create_tables)
    """

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db

    mock_scheduler = MagicMock()
    with (
        patch("app.main.init_db"),
        patch("app.main.setup_scheduler"),
        patch("app.main.scheduler", mock_scheduler),
    ):
        with TestClient(app, raise_server_exceptions=True) as c:
            yield c

    app.dependency_overrides.clear()
