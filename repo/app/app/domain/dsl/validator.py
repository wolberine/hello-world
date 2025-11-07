from __future__ import annotations

from typing import Any


def validate_dsl(dsl: dict[str, Any]) -> None:
    fields = dsl.get("fields") or {}
    if not isinstance(fields, dict):
        raise ValueError("fields must be a mapping")

    sm = dsl.get("state_machine")
    if not sm:
        return

    states = sm.get("states") or []
    if len(states) != len(set(states)):
        raise ValueError("state names must be unique")

    transitions = sm.get("transitions") or []
    for transition in transitions:
        name = transition.get("name")
        if not name:
            raise ValueError("transition missing name")
        from_states = transition.get("from")
        if isinstance(from_states, str):
            from_states = [from_states]
        if not from_states:
            raise ValueError(f"transition {name} must declare from")
        for state in from_states:
            if state not in states:
                raise ValueError(f"transition {name} references unknown from state {state}")
        to_state = transition.get("to")
        if to_state not in states:
            raise ValueError(f"transition {name} references unknown to state {to_state}")

    # relationships referencing fields
    for field_name in ("status", "amount", "balance"):
        if field_name not in fields:
            raise ValueError(f"required field {field_name} missing in DSL")
