"""Environment-backed application configuration."""

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    database_url: str
    jwt_secret: str
    jwt_issuer: str


def get_settings() -> Settings:
    database_url = os.getenv("DATABASE_URL", "").strip()
    jwt_secret = os.getenv("JWT_SECRET", "").strip()
    jwt_issuer = os.getenv("JWT_ISSUER", "zorentia-app").strip()
    if not database_url:
        raise RuntimeError("DATABASE_URL is required")
    if not jwt_secret:
        raise RuntimeError("JWT_SECRET is required")
    return Settings(
        database_url=database_url,
        jwt_secret=jwt_secret,
        jwt_issuer=jwt_issuer,
    )
