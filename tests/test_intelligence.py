from datetime import datetime, timezone
from src.anomaly import detect_anomalies
from src.duplicate import compare_records, detect_duplicates, normalized_identity
from src.feedback import correction_examples
from src.document_classifier import classify_text
from src.models import Correction, InvoiceRecord, ProcessingStatus

def base(**kwargs):
    value=InvoiceRecord(invoice_number="INV-10", invoice_date="2026-01-01", vendor_name="Acme Ltd", currency="USD", total_amount=100.0, status=ProcessingStatus.FOUND)
    for key,item in kwargs.items(): setattr(value,key,item)
    return value

def test_exact_and_identity_duplicates():
    old=base(source_sha256="abc",source_file="old.pdf"); new=base(source_sha256="abc",source_file="renamed.pdf")
    match=compare_records(new,old); assert match.category=="EXACT_DUPLICATE" and match.score==1.0
    assert normalized_identity(old)==normalized_identity(new)

def test_same_number_different_vendor_is_not_confirmed():
    old=base(vendor_name="Other Ltd",source_file="old.pdf"); new=base(source_file="new.pdf")
    assert compare_records(new,old).category=="NOT_DUPLICATE"

def test_batch_duplicate_sets_review_status():
    a=base(source_file="a.pdf"); b=base(source_file="b.pdf"); detect_duplicates([a,b])
    assert b.duplicate_status=="CONFIRMED_INVOICE_DUPLICATE" and b.status==ProcessingStatus.NEEDS_REVIEW

def test_anomaly_requires_history():
    history=[base(source_file=f"{i}.pdf",total_amount=float(i+100)) for i in range(5)]
    result=detect_anomalies(base(total_amount=1000),history)
    assert result.anomaly_alerts and result.anomaly_alerts[0].code=="VENDOR_TOTAL_OUTLIER"

def test_feedback_only_contains_verified_corrections():
    record=base(); record.corrections=[Correction("invoice_number","INV-10","INV-11",datetime.now(timezone.utc).isoformat())]
    examples=correction_examples([record]); assert examples[0]["user_verified"] is True and examples[0]["extraction_version"]

def test_document_classifier_rejects_purchase_order_as_invoice():
    result=classify_text("PURCHASE ORDER PO NUMBER 10 Supplier delivery terms")
    assert result.category=="purchase_order" and result.is_invoice is False
