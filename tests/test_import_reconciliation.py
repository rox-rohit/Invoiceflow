import csv
from decimal import Decimal

import pytest

from src.analytics import build_analytics
from src.importer import ImportService
from src.ledger import LedgerStore, LedgerTransaction
from src.reports import period_between
from datetime import date


def test_csv_import_preview_validation_provenance_and_idempotency(tmp_path):
    path = tmp_path / "sales.csv"
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["Date", "Customer", "Invoice Number", "Amount", "Currency"])
        writer.writerow(["2026-04-03", "North Shop", "S-1", "1200.45", "INR"])
        writer.writerow(["bad-date", "North Shop", "S-2", "50", "INR"])
        writer.writerow(["2026-04-03", "North Shop", "S-1", "1200.45", "INR"])
    store = LedgerStore(tmp_path / "db.sqlite")
    service = ImportService(store)
    preview = service.preview(path, "sales")
    assert (preview.valid_count, preview.invalid_count, preview.duplicate_count) == (1, 1, 1)
    result = service.confirm(preview)
    assert result["imported"] == 1
    row = store.conn.execute("SELECT import_batch_id,import_row_number,source_file FROM financial_transactions").fetchone()
    assert row[0] == result["batch_id"] and row[1] == 2 and row[2] == path.name
    assert service.confirm(preview)["already_imported"] is True
    assert len(store.list(verified_only=True)) == 1
    snapshot = build_analytics(store.list(verified_only=True), period_between(date(2026, 4, 1), date(2026, 4, 30)), "INR")
    assert snapshot.kpis["sales"]["value"] == Decimal("1200.45")
    store.close()


def test_excel_import_template_and_readback(tmp_path):
    store = LedgerStore(tmp_path / "db.sqlite")
    path = tmp_path / "purchases.xlsx"
    ImportService.write_template(path, "purchases", excel=True)
    from openpyxl import load_workbook
    book = load_workbook(path); sheet = book.active
    sheet.append(["2026-04-05", 250, "INR", "Supplier A", "P-1", "Stock", "Goods", 30, "Bank"]); book.save(path)
    preview = ImportService(store).preview(path, "purchases")
    assert preview.valid_count == 1 and preview.rows[0].transaction.transaction_type == "purchase"
    assert ImportService(store).confirm(preview)["imported"] == 1
    assert store.list(verified_only=True)[0].amount == Decimal("250.00")
    store.close()


def test_partial_allocation_exact_decimal_reverse_and_reconciliation(tmp_path):
    store = LedgerStore(tmp_path / "db.sqlite")
    sale = store.add(LedgerTransaction(transaction_type="sale", transaction_date="2026-04-01", amount="100.00", currency="INR", counterparty="Customer", verification_status="USER_REVIEWED"))
    collection = store.add(LedgerTransaction(transaction_type="collection", transaction_date="2026-04-02", amount="33.33", currency="INR", counterparty="Customer", verification_status="USER_REVIEWED"))
    allocation = store.allocate_payment(collection.transaction_id, sale.transaction_id, "33.33")
    assert store.allocation_summary(sale.transaction_id) == {"allocated": Decimal("33.33"), "remaining": Decimal("66.67"), "status": "partially_paid"}
    assert store.allocation_summary(collection.transaction_id)["remaining"] == Decimal("0.00")
    with pytest.raises(ValueError, match="unallocated payment"):
        store.allocate_payment(collection.transaction_id, sale.transaction_id, "0.01")
    store.reverse_allocation(allocation, "Wrong invoice selected")
    assert store.allocation_summary(sale.transaction_id)["remaining"] == Decimal("100.00")
    assert store.conn.execute("SELECT action FROM allocation_audit ORDER BY audit_id").fetchall()[-1][0] == "REVERSE"
    store.close()


def test_supplier_payment_allocates_to_purchase_only(tmp_path):
    payment_type, invoice_type = "supplier_payment", "purchase"
    store = LedgerStore(tmp_path / f"{payment_type}.db")
    invoice = store.add(LedgerTransaction(transaction_type=invoice_type, transaction_date="2026-04-01", amount="50", currency="INR", counterparty="Supplier", verification_status="VERIFIED"))
    payment = store.add(LedgerTransaction(transaction_type=payment_type, transaction_date="2026-04-02", amount="20", currency="INR", counterparty="Supplier", verification_status="VERIFIED"))
    store.allocate_payment(payment.transaction_id, invoice.transaction_id, "20")
    assert store.allocation_summary(invoice.transaction_id)["remaining"] == Decimal("30.00")
    with pytest.raises(ValueError, match="same business and counterparty"):
        mismatched = store.add(LedgerTransaction(transaction_type="supplier_payment", transaction_date="2026-04-02", amount="1", currency="INR", counterparty="Elsewhere", verification_status="VERIFIED"))
        store.allocate_payment(mismatched.transaction_id, invoice.transaction_id, "1")
    store.close()


def test_invoice_reversal_offsets_report_without_erasing_source(tmp_path):
    store = LedgerStore(tmp_path / "db.sqlite")
    sale = store.add(LedgerTransaction(transaction_type="sale", transaction_date="2026-04-01", amount="125", currency="INR", counterparty="Shop", verification_status="VERIFIED"))
    reversal = store.reverse(sale.transaction_id, "Entered twice")
    assert reversal.transaction_type == "sales_return"
    snapshot = build_analytics(store.list(verified_only=True), period_between(date(2026, 4, 1), date(2026, 4, 30)), "INR")
    assert snapshot.kpis["sales"]["value"] == Decimal("0.00")
    assert store.conn.execute("SELECT COUNT(*) FROM transaction_audit WHERE transaction_id=?", (sale.transaction_id,)).fetchone()[0] == 1
    assert store.conn.execute("SELECT COUNT(*) FROM financial_transactions WHERE metadata_json LIKE ?", (f'%"reverses_transaction_id": {sale.transaction_id}%',)).fetchone()[0] == 1
    store.close()


def test_migration_is_repeatable_and_foreign_keys_remain_valid(tmp_path):
    store = LedgerStore(tmp_path / "db.sqlite")
    original = store.add(LedgerTransaction(transaction_type="expense", transaction_date="2026-04-01", amount="9.99", currency="INR", verification_status="VERIFIED"))
    store.migrate(); store.migrate()
    assert store.list()[0].transaction_id == original.transaction_id
    assert store.conn.execute("PRAGMA foreign_key_check").fetchall() == []
    assert store.conn.execute("SELECT COUNT(*) FROM schema_migrations WHERE version=2").fetchone()[0] == 1
    store.close()
