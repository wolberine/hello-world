from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_run_claims
from app.core.config import settings
from app.db.models import Artifact, Run, Schedule, SdkCall
from app.schemas.outcomes import (
    CodeRequest,
    CodeResponse,
    PlanRequest,
    PlanResponse,
    RunRequest,
    RunResponse,
    ScheduleRequest,
    ScheduleResponse,
    SpecRequest,
    SpecResponse,
)
from app.schemas.sdk import EmailRequest, EmailResponse, QueryRequest, QueryResponse, SaveArtifactRequest, SaveArtifactResponse
from app.services.mailer import save_artifact_record, simulate_email
from app.services.policy import validate_code
from app.services.reports import aging_ar
from app.services.runner_client import RunnerError, invoke_runner
from app.services.scheduler import tick as scheduler_tick

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/reports/aging-ar")
def report_aging_ar(db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    return aging_ar(db)


@router.post("/outcomes/spec", response_model=SpecResponse)
def post_spec(request: SpecRequest, db: Session = Depends(get_db)) -> SpecResponse:
    artifact: Artifact
    if request.artifact_id:
        artifact = db.get(Artifact, request.artifact_id)
        if not artifact:
            raise HTTPException(status_code=404, detail="Artifact not found")
        artifact.spec_json = request.spec_json
        artifact.prompt = request.prompt
        artifact.user_id = request.user_id
    else:
        artifact = Artifact(
            user_id=request.user_id,
            prompt=request.prompt,
            spec_json=request.spec_json,
        )
        db.add(artifact)
        db.flush()
    return SpecResponse(artifact_id=artifact.id)


@router.post("/outcomes/plan", response_model=PlanResponse)
def post_plan(request: PlanRequest, db: Session = Depends(get_db)) -> PlanResponse:
    artifact = db.get(Artifact, request.artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")
    artifact.plan_json = request.plan_json
    return PlanResponse(artifact_id=artifact.id)


@router.post("/outcomes/code", response_model=CodeResponse)
def post_code(request: CodeRequest, db: Session = Depends(get_db)) -> CodeResponse:
    artifact = db.get(Artifact, request.artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")
    violations = validate_code(request.code)
    if violations:
        return CodeResponse(ok=False, violations=violations)
    artifact.code = request.code
    if request.model_version:
        artifact.model_version = request.model_version
    return CodeResponse(ok=True, violations=[])


@router.post("/outcomes/preview", response_model=RunResponse)
def preview_outcome(request: RunRequest, db: Session = Depends(get_db)) -> RunResponse:
    artifact = db.get(Artifact, request.artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")
    try:
        run, data = invoke_runner(
            db,
            artifact=artifact,
            user_id=str(artifact.user_id),
            mode="preview",
            limits=request.limits.dict(),
        )
    except RunnerError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    preview = data.get("preview") or data.get("result")
    return RunResponse(run_id=run.id, status=data.get("status", "preview"), preview=preview, logs=data.get("logs"))


@router.post("/outcomes/approve-run", response_model=RunResponse)
def approve_run(request: RunRequest, db: Session = Depends(get_db)) -> RunResponse:
    artifact = db.get(Artifact, request.artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")
    try:
        run, data = invoke_runner(
            db,
            artifact=artifact,
            user_id=str(artifact.user_id),
            mode="execute",
            limits=request.limits.dict(),
        )
    except RunnerError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return RunResponse(run_id=run.id, status=data.get("status", "executed"), preview=data.get("preview"), logs=data.get("logs"))


@router.post("/outcomes/schedule", response_model=ScheduleResponse)
def schedule_outcome(request: ScheduleRequest, db: Session = Depends(get_db)) -> ScheduleResponse:
    artifact = db.get(Artifact, request.artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")
    schedule = Schedule(artifact_id=artifact.id, cron=request.cron, enabled=True)
    db.add(schedule)
    db.flush()
    return ScheduleResponse(schedule_id=schedule.id)


@router.post("/_internal/tick")
def scheduler_tick_endpoint(db: Session = Depends(get_db)) -> dict[str, Any]:
    results = scheduler_tick(db)
    return {"results": results}


def _ensure_mode(claims: dict[str, Any], mode: str) -> None:
    if claims.get("mode") != mode:
        raise HTTPException(status_code=403, detail="Mode mismatch")


def _load_run(db: Session, claims: dict[str, Any]) -> Run:
    run_id = claims.get("run_id")
    if not run_id:
        raise HTTPException(status_code=400, detail="Missing run context")
    run = db.get(Run, uuid.UUID(run_id))
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


def _enforce_read_only(sql: str) -> None:
    lowered = " ".join(sql.strip().split()).lower()
    if not lowered.startswith("select") and not lowered.startswith("with"):
        raise HTTPException(status_code=400, detail="Only SELECT statements are allowed")
    for keyword in ("insert", "update", "delete", "drop", "alter", "create"):
        if keyword in lowered:
            raise HTTPException(status_code=400, detail="Only read-only queries are permitted")


@router.post("/sdk/query", response_model=QueryResponse)
def sdk_query(
    request: QueryRequest,
    claims: dict[str, Any] = Depends(get_run_claims),
    db: Session = Depends(get_db),
) -> QueryResponse:
    _ensure_mode(claims, request.mode)
    run = _load_run(db, claims)
    _enforce_read_only(request.sql)
    result = db.execute(text(request.sql), request.params or {})
    rows = [dict(row) for row in result.mappings().all()]
    if request.mode == "execute":
        db.add(
            SdkCall(
                run_id=run.id,
                api="query",
                params_json={"sql": request.sql, "params": request.params},
                result_meta_json={"row_count": len(rows)},
            )
        )
    return QueryResponse(rows=rows, row_count=len(rows))


@router.post("/sdk/email", response_model=EmailResponse)
def sdk_email(
    request: EmailRequest,
    claims: dict[str, Any] = Depends(get_run_claims),
    db: Session = Depends(get_db),
) -> EmailResponse:
    _ensure_mode(claims, request.mode)
    run = _load_run(db, claims)
    summary = simulate_email(
        db,
        run_id=str(run.id),
        mode=request.mode,
        to=request.to,
        cc=request.cc,
        subject=request.subject,
        body=request.body,
        attachments=[att.model_dump() for att in (request.attachments or [])],
    )
    return EmailResponse(summary=summary)


@router.post("/sdk/save_artifact", response_model=SaveArtifactResponse)
def sdk_save_artifact(
    request: SaveArtifactRequest,
    claims: dict[str, Any] = Depends(get_run_claims),
    db: Session = Depends(get_db),
) -> SaveArtifactResponse:
    _ensure_mode(claims, request.mode)
    run = _load_run(db, claims)
    record = save_artifact_record(db, str(run.id), request.mode, request.filename, request.content_base64)
    return SaveArtifactResponse(artifact=record)


@router.post("/runner/validate")
def validate_runner_token(claims: dict[str, Any] = Depends(get_run_claims)) -> dict[str, Any]:
    return {"claims": claims}
