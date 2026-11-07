from __future__ import annotations
import re
from .models import FieldEvidence, InvoiceRecord
from .pdf_extractor import PDFDocument

FIELD_LABELS={"invoice_number":r"invoice\s*(?:no|number)|bill\s*(?:no|number)|document\s+number","invoice_date":r"invoice\s+date|date\s+of\s+issue|bill\s+date","vendor_name":r"seller|vendor|supplier|sold\s+by","customer_name":r"buyer|customer|client|bill\s+to","subtotal":r"subtotal|net\s+(?:amount|total|worth)|taxable","tax_amount":r"tax|gst|vat","total_amount":r"grand\s+total|invoice\s+total|total\s+due|gross\s+worth|total"}

def attach_field_evidence(record: InvoiceRecord, document: PDFDocument) -> InvoiceRecord:
    for field, labels in FIELD_LABELS.items():
        value=getattr(record,field,None)
        if value in (None,""): continue
        page_number=None; coordinates=None; supporting=""; method="deterministic label parser"; score=0.62
        for page in document.pages:
            for line in page.text.splitlines():
                if re.search(labels,line,re.I):
                    page_number=page.number; supporting=line.strip(); score=0.82; method="label + line-context parser"; break
            if page_number: break
        if field in {"invoice_date","total_amount","subtotal"} and value not in (None,""): score=min(0.9,score+0.05)
        record.field_evidence[field]=FieldEvidence(value=value,normalized_value=value,confidence=round(score,3),method=method,page=page_number,coordinates=coordinates,supporting_text=supporting,calibrated=False,review_reason="Heuristic score; held-out calibration data is not yet available.")
    return record
