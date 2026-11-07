from datetime import date
from decimal import Decimal

from src.aging import build_aging
from src.ledger import LedgerStore, LedgerTransaction


def test_aging_uses_due_dates_and_allocations(tmp_path):
    store = LedgerStore(tmp_path / "aging.db")
    invoice = store.add(LedgerTransaction(
        transaction_type="sale", transaction_date="2026-10-01", due_date="2026-10-05",
        amount="100", currency="INR", counterparty="Shop", verification_status="VERIFIED",
    ))
    payment = store.add(LedgerTransaction(
        transaction_type="collection", transaction_date="2026-10-10",
        amount="40", currency="INR", counterparty="Shop", verification_status="VERIFIED",
    ))
    store.allocate_payment(payment.transaction_id, invoice.transaction_id, "40")
    rows = build_aging(store, date(2026, 11, 7), "receivable")
    assert rows[0].outstanding == Decimal("60.00")
    assert rows[0].allocated == Decimal("40.00")
    assert rows[0].bucket == "31–60 days overdue"
    store.close()
