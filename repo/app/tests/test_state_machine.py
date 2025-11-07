from __future__ import annotations

import uuid
from decimal import Decimal

from app.domain.state.engine import StateEngine
from app.domain.state.invoice_sm import init_invoice_state_machine
from app.db.models import DomainEvent, Invoice, Order
from app.db.session import session_scope


def test_invoice_state_transitions() -> None:
    engine = StateEngine()
    init_invoice_state_machine(engine)

    with session_scope() as session:
        order = Order(id=uuid.uuid4(), buyer_name="Test Buyer")
        session.add(order)
        session.flush()

        invoice = Invoice(
            id=uuid.uuid4(),
            order_id=order.id,
            buyer_email="buyer@example.com",
            status="issued",
            amount=Decimal("100.00"),
            balance=Decimal("100.00"),
        )
        session.add(invoice)
        session.flush()

        assert engine.can_transition(invoice, "invoice", "record_payment")
        engine.apply(session, invoice, "invoice", "record_payment", {"payment_amount": 25})
        session.flush()
        assert invoice.status == "partially_paid"
        assert invoice.balance == Decimal("75")

        assert engine.can_transition(invoice, "invoice", "settle")
        engine.apply(session, invoice, "invoice", "settle")
        session.flush()
        assert invoice.status == "paid"
        assert invoice.balance == Decimal("0")

        events = session.query(DomainEvent).filter_by(entity_id=invoice.id).all()
        assert len(events) >= 2
