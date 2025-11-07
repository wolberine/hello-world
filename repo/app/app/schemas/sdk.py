from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    sql: str
    params: dict[str, Any] | None = None
    mode: str = Field(..., pattern="^(preview|execute)$")


class QueryResponse(BaseModel):
    rows: list[dict[str, Any]]
    row_count: int


class EmailAttachment(BaseModel):
    filename: str
    content_base64: str


class EmailRequest(BaseModel):
    to: list[str]
    subject: str
    body: str
    cc: list[str] | None = None
    attachments: list[EmailAttachment] | None = None
    mode: str = Field(..., pattern="^(preview|execute)$")


class EmailResponse(BaseModel):
    summary: dict[str, Any]


class SaveArtifactRequest(BaseModel):
    filename: str
    content_base64: str
    mode: str = Field(..., pattern="^(preview|execute)$")


class SaveArtifactResponse(BaseModel):
    artifact: dict[str, Any]
