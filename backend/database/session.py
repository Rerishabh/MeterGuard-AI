"""
MeterGuard AI: Database Session & Engine Module
Configures SQLAlchemy connection pooling, SessionLocal, and FastAPI get_db dependency.
"""

from typing import Generator, Tuple, Optional
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.engine.url import make_url

from backend.app.config import settings

logger = logging.getLogger("meterguard.database")

# Build connection arguments supporting TiDB Cloud Serverless SSL/TLS requirements
connect_args = {}
db_url_str = (settings.DATABASE_URL or "").lower()

# TiDB Cloud Serverless requires secure transport (TLS/SSL).
# PyMySQL supports ssl_verify_cert and ssl_verify_identity flags, or query parameters in DATABASE_URL.
if "tidbcloud.com" in db_url_str:
    if "ssl_ca" not in db_url_str and "ssl_verify" not in db_url_str:
        connect_args["ssl_verify_cert"] = True
        connect_args["ssl_verify_identity"] = True

# Conservative connection pool settings for single low-memory Render instance
try:
    engine = create_engine(
        settings.DATABASE_URL,
        connect_args=connect_args,
        pool_pre_ping=True,
        pool_recycle=1800,
        pool_size=3,
        max_overflow=5,
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
    Actively tests the database connection by running 'SELECT 1'.
    Returns (True, None) if successful, or (False, error_message).
    Never leaks credentials in error reporting.
    """
    if engine is None:
        return False, "SQLAlchemy engine not initialized"
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True, None
    except Exception as exc:
        err_msg = str(exc)
        try:
            url_obj = make_url(settings.DATABASE_URL)
            if url_obj.password and url_obj.password in err_msg:
                err_msg = err_msg.replace(url_obj.password, "******")
        except Exception:
            pass
        logger.warning("Database connectivity check failed: %s", err_msg)
        return False, err_msg


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
