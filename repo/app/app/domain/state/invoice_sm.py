from __future__ import annotations

from pathlib import Path
from typing import Any

from app.domain.dsl.parser import load_dsl

from .engine import StateEngine, Transition


DSL_PATH = Path(__file__).resolve().parents[2] / "config" / "dsl" / "invoice.yaml"


def init_invoice_state_machine(engine: StateEngine) -> None:
    data = load_dsl(DSL_PATH)
    transitions: list[Transition] = []
    for trans in data.get("state_machine", {}).get("transitions", []):
        from_states = trans.get("from")
        if isinstance(from_states, str):
            from_states = [from_states]
        transitions.append(
            Transition(
                name=trans["name"],
                from_states=tuple(from_states or []),
                to_state=trans["to"],
            )
        )
    engine.register("invoice", transitions)
