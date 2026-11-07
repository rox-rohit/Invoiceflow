from __future__ import annotations
import re
from difflib import SequenceMatcher
from .models import DuplicateMatch, InvoiceRecord, ValidationIssue, ProcessingStatus

def normalize_text(value: str | None) -> str:
    value=(value or "").casefold()
    value=value.replace("0","o") if False else value
    return re.sub(r"[^a-z0-9]+", "", value)

def normalized_identity(record: InvoiceRecord) -> str:
    vendor=normalize_text(record.vendor_tax_id) or normalize_text(record.vendor_name)
    number=normalize_text(record.invoice_number)
    date=normalize_text(record.invoice_date)
    total="" if record.total_amount is None else f"{record.total_amount:.2f}"
    return "|".join((vendor,number,date,normalize_text(record.currency),total))

def _field_similarity(a: str, b: str) -> float:
    if not a or not b: return 0.0
    return SequenceMatcher(None, normalize_text(a), normalize_text(b)).ratio()

def compare_records(new: InvoiceRecord, old: InvoiceRecord) -> DuplicateMatch:
    if new.source_sha256 and new.source_sha256 == old.source_sha256:
        return DuplicateMatch("EXACT_DUPLICATE",1.0,old.record_id,old.source_file,["identical SHA-256 file hash"])
    evidence=[]; score=0.0; weight=0.0
    if new.invoice_number and old.invoice_number:
        number=_field_similarity(new.invoice_number,old.invoice_number); score += number*0.35; weight += 0.35
        if number >= 0.92: evidence.append("invoice numbers match closely")
    vendor=_field_similarity(new.vendor_tax_id or new.vendor_name,old.vendor_tax_id or old.vendor_name); score += vendor*0.30; weight += 0.30
    if vendor >= 0.92: evidence.append("vendor identity matches")
    if new.invoice_date and old.invoice_date:
        date=1.0 if new.invoice_date==old.invoice_date else 0.0; score += date*0.15; weight += 0.15
        if date: evidence.append("invoice dates match")
    if new.total_amount is not None and old.total_amount is not None:
        amount=1.0 if abs(new.total_amount-old.total_amount) <= max(0.02,abs(old.total_amount)*0.005) else 0.0; score += amount*0.20; weight += 0.20
        if amount: evidence.append("grand totals match")
    score=score/weight if weight else 0.0
    if new.invoice_number and old.invoice_number and new.invoice_number.casefold()==old.invoice_number.casefold() and vendor < 0.70:
        category="NOT_DUPLICATE"
    elif score >= 0.90 and new.invoice_number and (new.invoice_number == old.invoice_number or vendor >= 0.92): category="CONFIRMED_INVOICE_DUPLICATE"
    elif score >= 0.72: category="POSSIBLE_DUPLICATE"
    else: category="NOT_DUPLICATE"
    return DuplicateMatch(category,round(score,4),old.record_id,old.source_file,evidence)

def detect_duplicates(records: list[InvoiceRecord], existing: list[InvoiceRecord] | None = None) -> list[InvoiceRecord]:
    pool=list(existing or [])
    for index,record in enumerate(records):
        candidates=pool + records[:index]
        matches=[compare_records(record,old) for old in candidates if old.source_file != record.source_file or old.record_id != record.record_id]
        matches=[m for m in matches if m.category != "NOT_DUPLICATE"]
        record.duplicate_matches=matches
        if matches:
            best=max(matches,key=lambda m:m.score); record.duplicate_status=best.category; record.duplicate_score=best.score
            record.issues.append(ValidationIssue("DUPLICATE_CANDIDATE",f"{best.category.replace('_',' ').title()} ({best.score:.0%}). Review the matched record before importing both.","warning","source_file",best.matched_source))
            if record.status == ProcessingStatus.FOUND: record.status=ProcessingStatus.NEEDS_REVIEW
        else:
            record.duplicate_status="NOT_DUPLICATE"; record.duplicate_score=0.0
    return records
