from __future__ import annotations

import logging

from alembic import command
from alembic.config import Config
from fastapi import FastAPI

from app.api import routes
from app.db.seed import seed

logger = logging.getLogger(__name__)

app = FastAPI(title="AI Reporting Nucleus")
app.include_router(routes.router)


@app.on_event("startup")
def on_startup() -> None:
    config = Config("alembic.ini")
    command.upgrade(config, "head")
    try:
        seed()
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to seed data: %s", exc)


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "AI Reporting Nucleus"}
