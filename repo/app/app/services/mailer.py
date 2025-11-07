from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import SdkCall


def validate_recipients(addresses: list[str]) -> None:
    allowed = settings.allowed_email_domains
    for address in addresses:
        domain = address.split("@")[-1]
        if domain not in allowed:
            raise ValueError(f"Email domain '{domain}' is not allowed")


def simulate_email(
    session: Session,
    run_id: str,
    mode: str,
    *,
    to: list[str],
    cc: list[str] | None,
    subject: str,
    body: str,
    attachments: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    validate_recipients(to + (cc or []))
    summary = {
        "to": to,
        "cc": cc or [],
        "subject": subject,
        "body_preview": body[:200],
        "attachment_count": len(attachments or []),
    }
    if mode == "execute":
        call = SdkCall(
            run_id=run_id,
            api="email",
            params_json={"to": to, "cc": cc or [], "subject": subject},
            result_meta_json=summary,
        )
        session.add(call)
    return summary


def save_artifact_record(session: Session, run_id: str, mode: str, filename: str, content_b64: str) -> dict[str, Any]:
    record = {
        "filename": filename,
        "base64_preview": content_b64[:128],
    }
    if mode == "execute":
        call = SdkCall(
            run_id=run_id,
            api="save_artifact",
            params_json={"filename": filename},
            result_meta_json=record,
        )
        session.add(call)
    return record
