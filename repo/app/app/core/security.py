from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from jose import jwt

from .config import settings


def create_run_token(user_id: str, scopes: list[str], extra: dict[str, Any] | None = None) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": user_id,
        "scopes": scopes,
        "iat": int(now.timestamp()),
        "exp": int((now + settings.jwt_lifetime).timestamp()),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])


def require_scope(claims: dict[str, Any], scope: str) -> None:
    scopes = claims.get("scopes", [])
    if scope not in scopes:
        raise PermissionError(f"Missing required scope '{scope}'")
