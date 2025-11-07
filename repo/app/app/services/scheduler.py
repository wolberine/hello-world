from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.db.models import Schedule
from app.services.runner_client import RunnerError, invoke_runner

DEFAULT_LIMITS = {"cpu_ms": 500, "wall_ms": 2000, "mem_mb": 128}


def tick(session: Session) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    schedules = session.query(Schedule).filter_by(enabled=True).all()
    for schedule in schedules:
        artifact = schedule.artifact
        if not artifact or not artifact.code:
            continue
        try:
            run, data = invoke_runner(
                session,
                artifact=artifact,
                user_id=str(artifact.user_id),
                mode="execute",
                limits=DEFAULT_LIMITS,
            )
            results.append({"schedule_id": str(schedule.id), "run_id": str(run.id), "status": data.get("status")})
        except RunnerError as exc:
            results.append({"schedule_id": str(schedule.id), "error": str(exc)})
    session.commit()
    return results
