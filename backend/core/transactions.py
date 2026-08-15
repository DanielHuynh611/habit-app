"""Shared transaction helper."""

from contextlib import contextmanager

from backend.core.db import get_engine


@contextmanager
def transaction():
    with get_engine().begin() as connection:
        yield connection
