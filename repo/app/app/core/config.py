from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import timedelta


@dataclass
class Settings:
    postgres_host: str = os.getenv("POSTGRES_HOST", "localhost")
    postgres_port: int = int(os.getenv("POSTGRES_PORT", "5432"))
    postgres_db: str = os.getenv("POSTGRES_DB", "appdb")
    postgres_user: str = os.getenv("POSTGRES_USER", "app")
    postgres_password: str = os.getenv("POSTGRES_PASSWORD", "app")

    app_host: str = os.getenv("APP_HOST", "0.0.0.0")
    app_port: int = int(os.getenv("APP_PORT", "8000"))

    jwt_secret: str = os.getenv("JWT_SECRET", "devsecret")
    jwt_algorithm: str = "HS256"
    jwt_lifetime: timedelta = timedelta(seconds=120)

    allowed_email_domains: tuple[str, ...] = tuple(
        d.strip() for d in os.getenv("ALLOWED_EMAIL_DOMAINS", "example.com").split(",") if d.strip()
    )

    sdk_gateway_readonly: bool = os.getenv("SDK_GATEWAY_READONLY", "true").lower() == "true"
    sdk_gateway_url: str = os.getenv("SDK_GATEWAY_URL", "http://app:8000")
    runner_url: str = os.getenv("RUNNER_URL", "http://runner:8090")


settings = Settings()


def database_url() -> str:
    return (
        f"postgresql+psycopg://{settings.postgres_user}:{settings.postgres_password}"
        f"@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
    )
