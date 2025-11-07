from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

from app.core.config import settings
from app.core.security import create_run_token
from app.db.models import Artifact, Run
from app.utils.time import utc_now


class RunnerError(RuntimeError):
    pass


def invoke_runner(
    session,
    *,
    artifact: Artifact,
    user_id: str,
    mode: str,
    limits: dict[str, int],
) -> tuple[Run, dict[str, Any]]:
    if not artifact.code:
        raise RunnerError("Artifact has no code to execute")

    run = Run(
        artifact_id=artifact.id,
        user_id=user_id,
        status="running",
        started_at=utc_now(),
        limits_json=limits,
    )
    session.add(run)
    session.flush()

    run_token = create_run_token(
        user_id,
        scopes=["report", "email"],
        extra={"run_id": str(run.id), "artifact_id": str(artifact.id), "mode": mode},
    )

    payload = {
        "code": artifact.code,
        "run_token": run_token,
        "limits": limits,
        "mode": mode,
    }

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.post(f"{settings.runner_url}/execute", json=payload)
            response.raise_for_status()
            data = response.json()
    except Exception as exc:  # noqa: BLE001
        run.status = "failed"
        run.ended_at = utc_now()
        run.logs = str(exc)
        session.add(run)
        session.commit()
        raise RunnerError(str(exc)) from exc

    run.status = data.get("status", "completed")
    run.logs = data.get("logs", "")
    run.ended_at = utc_now()
    session.add(run)

    data.setdefault("run_id", str(run.id))
    return run, data
