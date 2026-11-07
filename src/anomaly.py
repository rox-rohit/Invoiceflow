from __future__ import annotations
from statistics import median
from .models import AnomalyAlert, InvoiceRecord

def _mad(values: list[float], value: float) -> float:
    center=median(values); spread=median([abs(x-center) for x in values]) or 0.0
    return abs(value-center)/(1.4826*spread) if spread else 0.0

def detect_anomalies(record: InvoiceRecord, history: list[InvoiceRecord]) -> InvoiceRecord:
    record.anomaly_alerts=[]; comparable=[x for x in history if x.vendor_name and record.vendor_name and x.vendor_name.casefold()==record.vendor_name.casefold() and x.total_amount is not None and x.status.value not in {"ERROR","NOT_AN_INVOICE"}]
    if len(comparable) >= 3 and record.total_amount is not None:
        values=[x.total_amount for x in comparable]
        score=_mad(values,record.total_amount)
        if score >= 3.5:
            record.anomaly_alerts.append(AnomalyAlert("VENDOR_TOTAL_OUTLIER","Invoice total is substantially different from this vendor's historical invoices; verify the amount.","warning",round(score,2),"total_amount",f"median={median(values):.2f}"))
    if record.tax_rate is not None and not 0 <= record.tax_rate <= 100:
        record.anomaly_alerts.append(AnomalyAlert("INVALID_TAX_RATE","Tax rate is outside the valid 0–100% range.","error",None,"tax_rate"))
    if len(record.line_items) != len({(x.description.casefold(),x.total) for x in record.line_items}):
        record.anomaly_alerts.append(AnomalyAlert("DUPLICATE_LINE_ITEM","The invoice contains repeated line-item description/amount pairs.","warning","line_items"))
    return record
