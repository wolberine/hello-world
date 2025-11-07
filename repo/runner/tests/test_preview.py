from __future__ import annotations

import os

from fastapi.testclient import TestClient
from jose import jwt

from runner.runner import nmc_sdk
from runner.runner.main import app


def setup_module(module) -> None:  # noqa: D401
    os.environ["JWT_SECRET"] = "devsecret"
    os.environ["SDK_GATEWAY_URL"] = "http://dummy"
    nmc_sdk.RUN_TOKEN = "test-token"
    nmc_sdk.MODE = "preview"


class DummyResponse:
    def __init__(self, data):
        self._data = data

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._data


class DummyClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    def __enter__(self) -> "DummyClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
        return None

    def post(self, path: str, json: dict) -> DummyResponse:
        self.calls.append((path, json))
        if path == "/sdk/email":
            return DummyResponse({"summary": {"sent": False, "to": json["to"]}})
        if path == "/sdk/query":
            return DummyResponse({"rows": [], "row_count": 0})
        if path == "/sdk/save_artifact":
            return DummyResponse({"artifact": {"filename": json["filename"], "base64_preview": ""}})
        return DummyResponse({})


def test_preview_execution(monkeypatch) -> None:
    dummy_client = DummyClient()
    monkeypatch.setattr(nmc_sdk, "_client", lambda: dummy_client)

    client = TestClient(app)
    code = "from nmc_sdk import email\nemail(['you@example.com'], 'Hi', 'Body')"
    token = jwt.encode({"mode": "preview"}, "devsecret", algorithm="HS256")
    payload = {
        "code": code,
        "run_token": token,
        "limits": {"cpu_ms": 500, "wall_ms": 1000, "mem_mb": 128},
        "mode": "preview",
    }

    response = client.post("/execute", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in {"ok", "error"}
    assert data["preview"]
    assert any(call[0] == "/sdk/email" for call in dummy_client.calls)
