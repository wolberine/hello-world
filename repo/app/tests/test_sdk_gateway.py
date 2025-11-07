from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from app.core.security import create_run_token
from app.db.models import Artifact, Run
from app.db.session import session_scope
from app.main import app


def _prepare_run(mode: str) -> str:
    with session_scope() as session:
        artifact = Artifact(user_id=uuid.uuid4(), prompt="p", spec_json={})
        session.add(artifact)
        session.flush()
        run = Run(artifact_id=artifact.id, user_id=artifact.user_id, status="running")
        session.add(run)
        session.flush()
        token = create_run_token(str(artifact.user_id), ["report", "email"], extra={"run_id": str(run.id), "mode": mode})
    return token


def test_sdk_query_allows_select_only() -> None:
    token = _prepare_run("preview")
    client = TestClient(app)

    res = client.post(
        "/sdk/query",
        headers={"Authorization": f"Bearer {token}"},
        json={"sql": "SELECT 1 AS value", "mode": "preview"},
    )
    assert res.status_code == 200
    payload = res.json()
    assert payload["row_count"] == 1

    bad = client.post(
        "/sdk/query",
        headers={"Authorization": f"Bearer {token}"},
        json={"sql": "DELETE FROM invoices", "mode": "preview"},
    )
    assert bad.status_code == 400
