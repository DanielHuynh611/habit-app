"""Shared lazy SQLAlchemy engine provider."""

from functools import lru_cache

from sqlalchemy import create_engine

from backend.core.config import get_settings


@lru_cache(maxsize=1)
def get_engine():
    return create_engine(
        get_settings().database_url,
        pool_pre_ping=True,
        future=True,
    )
