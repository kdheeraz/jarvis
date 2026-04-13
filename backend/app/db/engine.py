from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.config import get_config
from app.db.models import Base

_engine = None
_session_factory = None


def get_engine():
    global _engine
    if _engine is None:
        config = get_config()
        _engine = create_engine(
            config.database.url,
            echo=config.app.debug,
            connect_args={"check_same_thread": False} if "sqlite" in config.database.url else {},
        )
    return _engine


def get_session_factory():
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(bind=get_engine(), expire_on_commit=False)
    return _session_factory


def get_db() -> Session:
    """FastAPI dependency that yields a database session."""
    factory = get_session_factory()
    session = factory()
    try:
        yield session
    finally:
        session.close()


def init_db():
    """Create all tables. Used for initial setup / dev."""
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
