from __future__ import annotations
from datetime import date
from .models import InvoiceRecord, ProcessingStatus, ValidationIssue

def validate(record: InvoiceRecord, is_scanned: bool = False, is_invoice: bool = True) -> InvoiceRecord:
    record.issues = []
    if is_scanned:
        record.status = ProcessingStatus.REQUIRES_OCR
        record.issues.append(ValidationIssue("OCR_REQUIRED", "The PDF contains no usable text; OCR is required.", "error"))
        return record
    if not is_invoice:
        record.status = ProcessingStatus.NOT_AN_INVOICE
        record.issues.append(ValidationIssue("NOT_INVOICE", "No invoice indicators were found in the document.", "info"))
        return record
    if record.invoice_date_raw and not record.invoice_date:
        record.issues.append(ValidationIssue("INVALID_DATE", f"Invoice date '{record.invoice_date_raw}' could not be normalized.", "warning", "invoice_date"))
    if record.due_date_raw and not record.due_date:
        record.issues.append(ValidationIssue("INVALID_DATE", f"Due date '{record.due_date_raw}' could not be normalized.", "warning", "due_date"))
    for field, label in (("invoice_number", "Invoice number"), ("invoice_date", "Invoice date"), ("vendor_name", "Vendor name"), ("total_amount", "Total amount")):
        if not getattr(record, field):
            record.issues.append(ValidationIssue("MISSING_FIELD", f"{label} was not found.", "warning", field))
    if record.total_amount is not None and record.subtotal is not None and record.tax_amount is not None:
        expected = record.subtotal - (record.discount or 0) + record.tax_amount
        if abs(expected - record.total_amount) > max(0.02, abs(record.total_amount) * 0.01):
            record.issues.append(ValidationIssue("SUMMARY_MISMATCH", "Subtotal, discount, tax and total do not reconcile exactly.", "warning", "total_amount"))
    for field in ("subtotal", "discount", "taxable_amount", "tax_amount", "cgst", "sgst", "igst", "vat", "shipping_charges", "additional_charges", "total_amount", "amount_paid", "balance_due"):
        value = getattr(record, field)
        if value is not None and value < 0 and field not in {"discount"}:
            record.issues.append(ValidationIssue("INVALID_AMOUNT", f"{field.replace('_', ' ').title()} cannot be negative.", "error", field))
    for item in record.line_items:
        if item.quantity is not None and item.unit_price is not None and item.total is not None and abs(item.quantity * item.unit_price - item.total) > max(0.02, abs(item.total) * 0.03):
            record.issues.append(ValidationIssue("LINE_MISMATCH", "Line arithmetic differs; pack or unit pricing may explain the difference. Verify only if the invoice layout makes quantity × rate comparable.", "info", "line_items", item.description))
    record.status = ProcessingStatus.NEEDS_REVIEW if any(issue.severity in {"warning", "error"} for issue in record.issues) else ProcessingStatus.FOUND
    return record
