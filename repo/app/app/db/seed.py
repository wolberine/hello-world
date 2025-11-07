from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete

from app.db.models import Artifact, EmailDirectory, Invoice, Order, Payment, Run
from app.db.session import session_scope


def seed() -> None:
    now = datetime.now(timezone.utc)
    with session_scope() as session:
        for model in (Payment, Invoice, Order, EmailDirectory, Artifact, Run):
            session.execute(delete(model))

        buyers = [
            ("Acme Corp", "acme@example.com"),
            ("Globex", "billing@example.com"),
            ("Soylent", "finance@example.com"),
        ]

        orders: list[Order] = []
        for name, email in buyers:
            order = Order(id=uuid.uuid4(), buyer_name=name, created_at=now - timedelta(days=60), updated_at=now)
            orders.append(order)
            session.add(order)
            session.add(
                EmailDirectory(
                    entity="order",
                    entity_id=order.id,
                    role="billing",
                    address=email,
                    is_default=True,
                )
            )

        session.flush()

        invoices: list[Invoice] = []
        invoice_specs = [
            (orders[0], "issued", 1200.00, 1200.00, 45),
            (orders[0], "partially_paid", 900.00, 300.00, 35),
            (orders[1], "draft", 500.00, 500.00, 10),
            (orders[1], "issued", 750.00, 750.00, 20),
            (orders[2], "partially_paid", 2000.00, 1500.00, 60),
        ]
        for order, status, amount, balance, days_ago in invoice_specs:
            issued_at = now - timedelta(days=days_ago + 15)
            due_at = now - timedelta(days=days_ago)
            invoice = Invoice(
                id=uuid.uuid4(),
                order_id=order.id,
                buyer_email="finance@example.com" if order.buyer_name != "Acme Corp" else "ap@example.com",
                status=status,
                amount=amount,
                balance=balance,
                issued_at=issued_at,
                due_at=due_at,
                created_at=issued_at,
                updated_at=now,
            )
            invoices.append(invoice)
            session.add(invoice)

        session.flush()

        payments = [
            Payment(
                id=uuid.uuid4(),
                invoice_id=invoices[1].id,
                amount=600.00,
                received_at=now - timedelta(days=20),
            ),
            Payment(
                id=uuid.uuid4(),
                invoice_id=invoices[4].id,
                amount=500.00,
                received_at=now - timedelta(days=25),
            ),
        ]
        session.add_all(payments)

        session.commit()
        print("Seeded demo data")


if __name__ == "__main__":
    seed()
