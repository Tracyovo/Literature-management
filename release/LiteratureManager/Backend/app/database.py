from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import StaticPool

from .config import get_settings

Base = declarative_base()


@lru_cache(maxsize=1)
def get_engine():
    settings = get_settings()
    if settings.database_url.endswith(":memory:"):
        return create_engine(
            settings.database_url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    return create_engine(
        settings.database_url,
        connect_args={"check_same_thread": False},
    )


@lru_cache(maxsize=1)
def get_session_local():
    return sessionmaker(autocommit=False, autoflush=False, bind=get_engine())


def reset_engine() -> None:
    get_engine.cache_clear()
    get_session_local.cache_clear()


def get_db():
    session_local = get_session_local()
    db = session_local()
    try:
        yield db
    finally:
        db.close()
