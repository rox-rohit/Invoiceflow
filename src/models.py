from __future__ import annotations
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

class ProcessingStatus(str, Enum):
    FOUND = "FOUND"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    REQUIRES_OCR = "REQUIRES_OCR"
    NOT_AN_INVOICE = "NOT_AN_INVOICE"
    ERROR = "ERROR"

@dataclass
class LineItem:
    description: str = ""
    quantity: float | None = None
    unit: str = ""
    unit_price: float | None = None
    tax_rate: float | None = None
    tax_amount: float | None = None
    total: float | None = None
    sku: str = ""
    hsn_sac: str = ""
    discount: float | None = None
    source_row: int | None = None

@dataclass
class ValidationIssue:
    code: str
    message: str
    severity: str = "warning"
    field: str = ""
    context: str = ""

@dataclass
class Correction:
    field_name: str
    original_value: Any
    corrected_value: Any
    timestamp: str

@dataclass
class FieldEvidence:
    value: Any = None
    normalized_value: Any = None
    confidence: float = 0.0
    method: str = ""
    page: int | None = None
    coordinates: tuple[float, float, float, float] | None = None
    supporting_text: str = ""
    calibrated: bool = False
    review_reason: str = ""

@dataclass
class DuplicateMatch:
    category: str
    score: float
    matched_record_id: int | None = None
    matched_source: str = ""
    evidence: list[str] = field(default_factory=list)
    decision: str = "unresolved"

@dataclass
class AnomalyAlert:
    code: str
    message: str
    severity: str = "warning"
    score: float | None = None
    field: str = ""
    expected: str = ""

@dataclass
class InvoiceRecord:
    record_id: int | None = field(default=None, repr=False)
    source_file: str = ""
    invoice_number: str = ""
    invoice_date: str = ""
    due_date: str = ""
    vendor_name: str = ""
    vendor_address: str = ""
    vendor_tax_id: str = ""
    customer_name: str = ""
    customer_address: str = ""
    customer_tax_id: str = ""
    currency: str = ""
    subtotal: float | None = None
    discount: float | None = None
    tax_rate: float | None = None
    tax_amount: float | None = None
    total_amount: float | None = None
    payment_terms: str = ""
    purchase_order_number: str = ""
    reference_number: str = ""
    invoice_type: str = ""
    document_type: str = "invoice"
    vendor_email: str = ""
    vendor_phone: str = ""
    customer_billing_address: str = ""
    customer_shipping_address: str = ""
    taxable_amount: float | None = None
    cgst: float | None = None
    sgst: float | None = None
    igst: float | None = None
    vat: float | None = None
    shipping_charges: float | None = None
    additional_charges: float | None = None
    amount_paid: float | None = None
    balance_due: float | None = None
    bank_details: str = ""
    notes: str = ""
    invoice_date_raw: str = ""
    due_date_raw: str = ""
    source_sha256: str = ""
    extraction_version: str = "2.0-deterministic"
    field_evidence: dict[str, FieldEvidence] = field(default_factory=dict, repr=False)
    duplicate_status: str = "NOT_DUPLICATE"
    duplicate_score: float = 0.0
    duplicate_matches: list[DuplicateMatch] = field(default_factory=list, repr=False)
    anomaly_alerts: list[AnomalyAlert] = field(default_factory=list, repr=False)
    original_data: dict[str, Any] = field(default_factory=dict, repr=False)
    corrections: list[Correction] = field(default_factory=list, repr=False)
    line_items: list[LineItem] = field(default_factory=list)
    status: ProcessingStatus = ProcessingStatus.NEEDS_REVIEW
    issues: list[ValidationIssue] = field(default_factory=list)
    processing_seconds: float = 0.0
    manually_corrected: set[str] = field(default_factory=set, repr=False)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        data["manually_corrected"] = sorted(self.manually_corrected)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "InvoiceRecord":
        data = dict(data)
        data["status"] = ProcessingStatus(data.get("status", ProcessingStatus.NEEDS_REVIEW))
        data["line_items"] = [LineItem(**x) for x in data.get("line_items", [])]
        data["issues"] = [ValidationIssue(**x) for x in data.get("issues", [])]
        data["corrections"] = [Correction(**x) for x in data.get("corrections", [])]
        data["field_evidence"] = {k: FieldEvidence(**v) for k,v in data.get("field_evidence", {}).items()}
        data["duplicate_matches"] = [DuplicateMatch(**x) for x in data.get("duplicate_matches", [])]
        data["anomaly_alerts"] = [AnomalyAlert(**x) for x in data.get("anomaly_alerts", [])]
        data["manually_corrected"] = set(data.get("manually_corrected", []))
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
