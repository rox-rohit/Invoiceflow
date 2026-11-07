from __future__ import annotations
import re, time
from .models import InvoiceRecord
from .pdf_extractor import PDFDocument
from .table_extractor import extract_line_items
from .utils import normalize_space, parse_amount, parse_date_token
from .validator import validate
from .confidence import attach_field_evidence
from .document_classifier import classify_text

LABELS = {
    "invoice_number": r"invoice\s*(?:no\.?|number|#)|bill\s*(?:no\.?|number)|tax\s+invoice\s*(?:no\.?|number)|document\s+number",
    "invoice_date": r"invoice\s+date|bill\s+date|date\s+of\s+issue|issued\s+on",
    "due_date": r"due\s+date|payment\s+due",
    "vendor_name": r"seller|vendor|supplier|sold\s+by|bill\s+from",
    "customer_name": r"buyer|customer|client|bill\s+to|ship\s+to",
}
DATE_TOKEN = r"(\d{1,4}[./-]\d{1,2}[./-]\d{2,4}|\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}|[A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4})"

def _lines(text: str) -> list[str]:
    return [normalize_space(line) for line in text.splitlines() if normalize_space(line)]

def _label_value(lines: list[str], labels: str) -> str:
    pattern = re.compile(rf"^(?:{labels})\s*[:#\-]?\s*(.*)$", re.I)
    for index, line in enumerate(lines):
        match = pattern.match(line)
        if match:
            value = normalize_space(match.group(1))
            if value:
                return value
            if index + 1 < len(lines) and not re.match(r"^[A-Za-z ]+\s*:", lines[index + 1]):
                return lines[index + 1]
    return ""

def _amount(lines: list[str], labels: str) -> float | None:
    pattern = re.compile(rf"^(?:{labels})\s*[:#\-]?\s*([^\n]+)$", re.I)
    for line in lines:
        match = pattern.match(line)
        if match:
            value = parse_amount(match.group(1))
            if value is not None:
                return value
    for index, line in enumerate(lines):
        if re.search(rf"(?<!\w)(?:{labels})(?!\w)", line, re.I) and index + 1 < len(lines):
            value = parse_amount(lines[index + 1])
            if value is not None:
                return value
    return None

def _tax_amount(lines: list[str], label: str) -> float | None:
    return _amount(lines, rf"(?:total\s+)?{label}(?:\s+amount)?")

def parse_invoice(document: PDFDocument) -> InvoiceRecord:
    started = time.perf_counter(); lines = _lines(document.text); text = "\n".join(lines)
    record = InvoiceRecord(source_file=str(document.path))
    record.invoice_number = _label_value(lines, LABELS["invoice_number"])
    record.invoice_date_raw = _label_value(lines, LABELS["invoice_date"]); record.due_date_raw = _label_value(lines, LABELS["due_date"])
    match = re.search(DATE_TOKEN, record.invoice_date_raw); due = re.search(DATE_TOKEN, record.due_date_raw)
    record.invoice_date = parse_date_token(match.group(1)) if match else parse_date_token(record.invoice_date_raw)
    record.due_date = parse_date_token(due.group(1)) if due else parse_date_token(record.due_date_raw)
    record.vendor_name = _label_value(lines, LABELS["vendor_name"]); record.customer_name = _label_value(lines, LABELS["customer_name"])
    record.vendor_tax_id = _label_value(lines, r"(?:vendor\s+)?(?:gstin|gst\s*no|tax\s*id|vat\s*no|registration\s+number)")
    record.customer_tax_id = _label_value(lines, r"(?:customer\s+)?(?:gstin|gst\s*no|tax\s*id|vat\s*no|registration\s+number)")
    record.vendor_email = next((x for x in lines if re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", x)), "")
    record.vendor_phone = next((x for x in lines if re.search(r"(?:phone|tel|mobile)\s*[:#-]?\s*[+\d][\d ()-]{6,}", x, re.I)), "")
    currency = re.search(r"(\u20b9|INR|USD|EUR|GBP|\$|\u20ac|\u00a3)", text, re.I); record.currency = currency.group(1) if currency else ""
    record.subtotal = _amount(lines, r"(?:subtotal|net\s+(?:amount|total|worth)|taxable\s+(?:amount|value))"); record.taxable_amount = _amount(lines, r"(?:taxable\s+(?:amount|value))")
    record.discount = _amount(lines, r"discount"); record.cgst = _tax_amount(lines, "cgst"); record.sgst = _tax_amount(lines, "sgst"); record.igst = _tax_amount(lines, "igst"); record.vat = _tax_amount(lines, "vat")
    record.tax_amount = _amount(lines, r"(?:total\s+tax|tax\s+amount|gst|igst|cgst|sgst|vat|sales\s+tax)")
    rate = re.search(r"(?:tax|gst|vat)[^\n%]{0,20}(\d+(?:\.\d+)?)\s*%", text, re.I); record.tax_rate = float(rate.group(1)) if rate else None
    record.shipping_charges = _amount(lines, r"(?:shipping|freight|delivery)\s+(?:charges?|fee)"); record.additional_charges = _amount(lines, r"(?:additional|other|miscellaneous)\s+charges?")
    record.total_amount = _amount(lines, r"(?:grand\s+total|invoice\s+total|total\s+due|amount\s+due|balance\s+due|gross\s+worth|total)"); record.amount_paid = _amount(lines, r"amount\s+paid|paid\s+amount"); record.balance_due = _amount(lines, r"balance\s+due|outstanding")
    if "SUMMARY" in (x.upper() for x in lines):
        summary_index=next(i for i,x in enumerate(lines) if x.upper()=="SUMMARY")
        summary_values=[parse_amount(x.replace("%", "")) for x in lines[summary_index+1:] if parse_amount(x.replace("%", "")) is not None]
        if len(summary_values)>=3:
            record.subtotal=summary_values[-3] if record.subtotal is None else record.subtotal
            record.tax_amount=summary_values[-2] if record.tax_amount is None else record.tax_amount
            record.total_amount=summary_values[-1]
    record.payment_terms = _label_value(lines, r"payment\s+terms?"); record.purchase_order_number = _label_value(lines, r"(?:purchase\s+order|po)\s*(?:no\.?|number|#)?"); record.reference_number = _label_value(lines, r"reference\s+(?:no\.?|number)"); record.invoice_type = _label_value(lines, r"invoice\s+type")
    record.bank_details = _label_value(lines, r"bank\s+details?|account\s+details?"); record.notes = _label_value(lines, r"notes?|remarks?|comments?"); record.line_items = extract_line_items(document.text); record.processing_seconds = time.perf_counter() - started
    classification=classify_text(text,document.is_scanned); record.document_type=classification.category
    evidence = len(re.findall(r"\b(invoice|bill|seller|vendor|supplier|subtotal|net worth|amount due|grand total|gross worth|tax invoice)\b", text, re.I))
    attach_field_evidence(record, document)
    return validate(record, document.is_scanned, classification.is_invoice or evidence >= 2 or bool(record.invoice_number and (record.vendor_name or record.total_amount is not None)))
