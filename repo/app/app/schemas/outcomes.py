from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from .common import LimitsModel


class SpecRequest(BaseModel):
    artifact_id: UUID | None = None
    user_id: UUID
    prompt: str
    spec_json: dict[str, Any]


class SpecResponse(BaseModel):
    artifact_id: UUID


class PlanRequest(BaseModel):
    artifact_id: UUID
    plan_json: dict[str, Any]


class PlanResponse(BaseModel):
    artifact_id: UUID


class CodeRequest(BaseModel):
    artifact_id: UUID
    code: str
    model_version: str | None = None


class CodeResponse(BaseModel):
    ok: bool
    violations: list[str]


class RunRequest(BaseModel):
    artifact_id: UUID
    limits: LimitsModel


class RunResponse(BaseModel):
    run_id: UUID
    status: str
    preview: dict[str, Any] | None = None
    logs: str | None = None


class ScheduleRequest(BaseModel):
    artifact_id: UUID
    cron: str


class ScheduleResponse(BaseModel):
    schedule_id: UUID
