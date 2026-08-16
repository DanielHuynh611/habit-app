"""Shared lazy SQLAlchemy engine provider."""

from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url

from backend.core.config import get_settings


@lru_cache(maxsize=1)
def get_engine():
    database_url = get_settings().database_url
    connect_args = {}
    if make_url(database_url).get_backend_name() == "mysql":
        connect_args["connection_timeout"] = 5
    return create_engine(
        database_url,
        connect_args=connect_args,
        pool_pre_ping=True,
        future=True,
    )
