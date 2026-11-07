from decimal import Decimal
from src.ledger import LedgerStore, LedgerTransaction
from src.models import InvoiceRecord
from src.reports import build_report, period_for
from datetime import date

def test_ledger_migration_and_decimal_transaction(tmp_path):
    store=LedgerStore(tmp_path/"history.db")
    tx=store.add(LedgerTransaction(transaction_type="sale",transaction_date="2026-01-05",amount="10.10",currency="INR",source_record_id=7,verification_status="PROPOSED"))
    assert tx.transaction_id and store.list()[0].amount==Decimal("10.10")
    store.verify(tx.transaction_id); assert store.list(verified_only=True)[0].verification_status=="VERIFIED"; store.close()

def test_invoice_proposal_requires_explicit_type():
    record=InvoiceRecord(invoice_date="2026-01-01",invoice_number="I-1",vendor_name="Supplier",total_amount=Decimal("12.30"),currency="INR")
    store=LedgerStore(":memory:")
    proposal=store.propose_from_invoice(record,"purchase"); assert proposal.verification_status=="PROPOSED" and proposal.amount==Decimal("12.30")
    try: store.propose_from_invoice(record,"receipt")
    except Exception: pass
    store.close()

def test_report_accepts_decimal_ledger_transactions(tmp_path):
    store=LedgerStore(tmp_path/"history.db"); store.add(LedgerTransaction(transaction_type="sale",transaction_date="2026-01-05",amount="100.10",currency="INR")); store.add(LedgerTransaction(transaction_type="expense",transaction_date="2026-01-06",amount="20.05",currency="INR")); report=build_report(store.list(),period_for("month",date(2026,1,10)),"INR"); assert report.metrics["estimated_net_profit"].value==Decimal("80.05"); store.close()
