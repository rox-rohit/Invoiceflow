from pathlib import Path
from src.models import ProcessingStatus
from src.utils import parse_amount, parse_date_token
from src.validator import validate
from src.models import InvoiceRecord

def test_amount_and_dates():
    assert parse_amount("₹1,234.50") == 1234.5
    assert parse_date_token("2026-11-07") == "2026-11-07"

def test_non_invoice_is_explicit():
    r=validate(InvoiceRecord(), is_invoice=False)
    assert r.status == ProcessingStatus.NOT_AN_INVOICE

def test_pack_pricing_is_review_not_rewritten():
    r=InvoiceRecord(invoice_number="A-1", invoice_date="2026-01-01", vendor_name="Acme", total_amount=100, subtotal=80, tax_amount=20)
    r.line_items=[]; validate(r, is_invoice=True)
    assert r.total_amount == 100

def test_roundtrip_model():
    r=InvoiceRecord(invoice_number="A", status=ProcessingStatus.FOUND)
    assert InvoiceRecord.from_dict(r.to_dict()).invoice_number == "A"
