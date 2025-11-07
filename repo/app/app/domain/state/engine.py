from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict

from sqlalchemy.orm import Session

from app.db.models import DomainEvent, Invoice


@dataclass
class Transition:
    name: str
    from_states: tuple[str, ...]
    to_state: str


class StateEngine:
    def __init__(self) -> None:
        self._machines: Dict[str, Dict[str, Transition]] = {}

    def register(self, name: str, transitions: list[Transition]) -> None:
        self._machines[name] = {t.name: t for t in transitions}

    def can_transition(self, entity: Any, sm_name: str, transition_name: str) -> bool:
        machine = self._machines.get(sm_name)
        if not machine:
            raise KeyError(f"Unknown state machine {sm_name}")
        transition = machine.get(transition_name)
        if not transition:
            raise KeyError(f"Unknown transition {transition_name}")
        current = getattr(entity, "status")
        return current in transition.from_states

    def apply(
        self,
        session: Session,
        entity: Any,
        sm_name: str,
        transition_name: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        machine = self._machines.get(sm_name)
        if not machine:
            raise KeyError(f"Unknown state machine {sm_name}")
        transition = machine.get(transition_name)
        if not transition:
            raise KeyError(f"Unknown transition {transition_name}")
        if not self.can_transition(entity, sm_name, transition_name):
            raise ValueError(f"Cannot apply {transition_name} from {entity.status}")

        entity.status = transition.to_state
        if isinstance(entity, Invoice):
            self._update_invoice_financials(entity, transition_name, payload)

        event = DomainEvent(
            event_type="state_transition",
            entity_type=entity.__class__.__name__,
            entity_id=getattr(entity, "id"),
            payload={
                "transition": transition_name,
                "to": transition.to_state,
                "payload": payload or {},
            },
        )
        session.add(event)

    def _update_invoice_financials(
        self, invoice: Invoice, transition_name: str, payload: dict[str, Any] | None
    ) -> None:
        payload = payload or {}
        if transition_name == "record_payment":
            amount = Decimal(str(payload.get("payment_amount", 0)))
            invoice.balance = max(Decimal("0"), invoice.balance - amount)
        elif transition_name == "settle":
            invoice.balance = Decimal("0")
