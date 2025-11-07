from __future__ import annotations

import base64
import os
from datetime import datetime, timezone
from io import StringIO
from typing import Any, Dict, List

import csv
import httpx

RUN_TOKEN = os.getenv("RUN_TOKEN")
SDK_GATEWAY_URL = os.getenv("SDK_GATEWAY_URL", "http://app:8000")
MODE = os.getenv("MODE", "preview")

_CALL_LOG: List[Dict[str, Any]] = []


def _client() -> httpx.Client:
    if not RUN_TOKEN:
        raise RuntimeError("RUN_TOKEN missing")
    headers = {"Authorization": f"Bearer {RUN_TOKEN}"}
    return httpx.Client(base_url=SDK_GATEWAY_URL, headers=headers, timeout=5.0)


def _log(api: str, params: dict[str, Any], result: dict[str, Any]) -> None:
    _CALL_LOG.append({"api": api, "params": params, "result": result})


def get_call_log() -> list[dict[str, Any]]:
    return list(_CALL_LOG)


def clear_call_log() -> None:
    _CALL_LOG.clear()


def query(sql: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    payload = {"sql": sql, "params": params, "mode": MODE}
    with _client() as client:
        resp = client.post("/sdk/query", json=payload)
        resp.raise_for_status()
        data = resp.json()
    _log("query", payload, {"row_count": data.get("row_count")})
    return data.get("rows", [])


def to_csv(rows: list[dict[str, Any]]) -> bytes:
    if not rows:
        return b""
    fieldnames = list(rows[0].keys())
    buf = StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return buf.getvalue().encode("utf-8")


def email(
    to: list[str],
    subject: str,
    body: str,
    cc: list[str] | None = None,
    attachments: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    payload = {
        "to": to,
        "cc": cc or [],
        "subject": subject,
        "body": body,
        "attachments": attachments or [],
        "mode": MODE,
    }
    with _client() as client:
        resp = client.post("/sdk/email", json=payload)
        resp.raise_for_status()
        data = resp.json()
    _log("email", payload, data.get("summary", {}))
    return data


def save_artifact(filename: str, content_bytes: bytes) -> dict[str, Any]:
    payload = {
        "filename": filename,
        "content_base64": base64.b64encode(content_bytes).decode("utf-8"),
        "mode": MODE,
    }
    with _client() as client:
        resp = client.post("/sdk/save_artifact", json=payload)
        resp.raise_for_status()
        data = resp.json()
    _log("save_artifact", {"filename": filename}, data.get("artifact", {}))
    return data.get("artifact", {})


def now() -> str:
    return datetime.now(timezone.utc).isoformat()
