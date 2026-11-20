"""
MeterGuard AI: Database Session & Engine Module
Configures SQLAlchemy connection pooling, SessionLocal, and FastAPI get_db dependency.
"""

from typing import Generator, Tuple, Optional
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError

from backend.app.config import settings

logger = logging.getLogger("meterguard.database")

# Create engine with production-ready connection pool settings
# pool_pre_ping checks connectivity before handing out connections
# pool_recycle refreshes connections before MySQL wait_timeout (typically 28800s, 3600s is safe)
try:
    engine = create_engine(
        settings.DATABASE_URL,
        pool_pre_ping=True,
        pool_recycle=3600,
        pool_size=10,
        max_overflow=20,
    )
except Exception as exc:
    logger.error("Failed to initialize SQLAlchemy engine: %s", exc)
    engine = None

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
) if engine is not None else None


def check_db_connection() -> Tuple[bool, Optional[str]]:
    """
    Actively tests the MySQL connection by running 'SELECT 1'.
    Returns (True, None) if successful, or (False, error_message).
    """
    if engine is None:
        return False, "SQLAlchemy engine not initialized"
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, None
    except Exception as exc:
        logger.warning("Database connectivity check failed: %s", exc)
        return False, str(exc)


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that provides a transactional database session per request.
    Properly closes the session after request completion.
    """
    if SessionLocal is None:
        raise RuntimeError("Database engine not configured or unavailable.")

    db: Session = SessionLocal()
    try:
        yield db
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error("Database session error occurred; rolling back: %s", exc)
        raise
    finally:
        db.close()
