"""
Database engine — SQLite-backed session factory for the design management platform.

Usage:
    from web.backend.db.engine import get_engine, get_session, init_db
    init_db("data/implcraft.db")
    with get_session() as session:
        session.add(record)
"""
from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from .models import Base

_engine: Engine | None = None
_session_factory: sessionmaker | None = None


def get_engine(db_path: str | Path | None = None) -> Engine:
    """Get or create the global SQLAlchemy engine."""
    global _engine
    if _engine is not None:
        return _engine

    if db_path is None:
        db_path = os.environ.get("IMPLCRAFT_DB", "data/implcraft.db")

    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    url = f"sqlite:///{db_path}"
    _engine = create_engine(
        url,
        echo=False,
        pool_pre_ping=True,
        connect_args={
            "check_same_thread": False,
            "timeout": 30,
        },
    )

    @event.listens_for(_engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA cache_size=-64000")  # 64MB cache
        cursor.close()

    return _engine


def get_session_factory() -> sessionmaker:
    """Get or create the session factory."""
    global _session_factory
    if _session_factory is not None:
        return _session_factory

    engine = get_engine()
    _session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    return _session_factory


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """Context manager for database sessions."""
    factory = get_session_factory()
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db(db_path: str | Path | None = None) -> Engine:
    """Initialize the database — create all tables."""
    engine = get_engine(db_path)
    Base.metadata.create_all(engine)
    return engine


def reset_engine():
    """Reset global engine/session (for testing)."""
    global _engine, _session_factory
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _session_factory = None
