from __future__ import annotations

from pydantic import BaseModel, Field


class LimitsModel(BaseModel):
    cpu_ms: int = Field(..., ge=1, le=10000)
    wall_ms: int = Field(..., ge=1, le=60000)
    mem_mb: int = Field(..., ge=16, le=1024)
