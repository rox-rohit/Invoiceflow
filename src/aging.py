from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from .ledger import LedgerStore, LedgerTransaction


@dataclass
class AgingRow:
    party: str
    reference: str
    invoice_date: str
    due_date: str
    original: Decimal
    allocated: Decimal
    outstanding: Decimal
    days_overdue: int | None
    bucket: str
    source_id: int | None


def _bucket(days: int | None) -> str:
    if days is None or days <= 0:
        return "Not due"
    if days <= 30:
        return "1–30 days overdue"
    if days <= 60:
        return "31–60 days overdue"
    if days <= 90:
        return "61–90 days overdue"
    return "More than 90 days overdue"


def build_aging(store: LedgerStore, as_of: date, role: str) -> list[AgingRow]:
    invoice_type = "sale" if role == "receivable" else "purchase"
    rows = []
    for tx in store.list(verified_only=True):
        if tx.transaction_type != invoice_type:
            continue
        outstanding = store.allocation_summary(tx.transaction_id)["remaining"]
        if outstanding <= 0:
            continue
        due = tx.due_date or tx.transaction_date
        try:
            days = (as_of - date.fromisoformat(due[:10])).days
        except ValueError:
            days = None
        rows.append(AgingRow(
            tx.counterparty or "Unassigned",
            tx.reference_number or "—",
            tx.transaction_date,
            due,
            tx.amount or Decimal("0.00"),
            store.allocation_summary(tx.transaction_id)["allocated"],
            outstanding,
            days,
            _bucket(days),
            tx.transaction_id,
        ))
    return rows
