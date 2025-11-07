from __future__ import annotations

from datetime import timedelta

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.db.models import Invoice, Order
from app.utils.time import utc_now


def aging_ar(session: Session) -> list[dict[str, object]]:
    cutoff = utc_now() - timedelta(days=30)
    stmt: Select = (
        select(
            Invoice.id.label("invoice_id"),
            Order.buyer_name,
            Invoice.buyer_email,
            Invoice.amount,
            Invoice.balance,
            Invoice.due_at,
        )
        .join(Order, Invoice.order_id == Order.id)
        .where(Invoice.status.in_(["issued", "partially_paid"]))
        .where(Invoice.due_at < cutoff)
        .order_by(Invoice.due_at.asc())
    )
    rows = session.execute(stmt).mappings().all()
    return [dict(row) for row in rows]
