from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI, HTTPException
from jose import jwt
from pydantic import BaseModel, Field

from .sandbox import run_user_code

JWT_SECRET = os.getenv("JWT_SECRET", "devsecret")
JWT_ALGORITHM = "HS256"
SDK_GATEWAY_URL = os.getenv("SDK_GATEWAY_URL", "http://app:8000")

app = FastAPI(title="Runner Service")


class LimitsModel(BaseModel):
    cpu_ms: int = Field(..., ge=1)
    wall_ms: int = Field(..., ge=1)
    mem_mb: int = Field(..., ge=16)


class ExecuteRequest(BaseModel):
    code: str
    run_token: str
    limits: LimitsModel
    mode: str = Field(..., pattern="^(preview|execute)$")


class ExecuteResponse(BaseModel):
    status: str
    stdout: str
    stderr: str | None = None
    logs: str | None = None
    preview: list[dict[str, Any]] | None = None
    sdk_calls: list[dict[str, Any]] | None = None


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def _validate_token(token: str, mode: str) -> dict[str, Any]:
    try:
        claims = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=401, detail="Invalid token") from exc
    if claims.get("mode") != mode:
        raise HTTPException(status_code=403, detail="Mode mismatch")
    return claims


@app.post("/execute", response_model=ExecuteResponse)
def execute(request: ExecuteRequest) -> ExecuteResponse:
    _validate_token(request.run_token, request.mode)
    env = {
        "RUN_TOKEN": request.run_token,
        "SDK_GATEWAY_URL": SDK_GATEWAY_URL,
        "MODE": request.mode,
    }
    wall_time_s = max(1, request.limits.wall_ms // 1000)
    result = run_user_code(request.code, env, wall_time_s, request.limits.mem_mb)
    preview: list[dict[str, Any]] | None = None
    if request.mode == "preview":
        preview = [{"api": call.get("api"), "result": call.get("result") } for call in result.get("sdk_calls", [])]
    return ExecuteResponse(
        status=result.get("status", "error"),
        stdout=result.get("stdout", ""),
        stderr=result.get("stderr"),
        logs=result.get("error") or result.get("stderr"),
        preview=preview,
        sdk_calls=result.get("sdk_calls", []),
    )


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "Runner"}
