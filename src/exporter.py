from __future__ import annotations
import csv, json
from pathlib import Path
from .models import InvoiceRecord

def _summary(record: InvoiceRecord) -> dict:
    return {"invoice_number":record.invoice_number,"invoice_date":record.invoice_date,"vendor_name":record.vendor_name,"customer_name":record.customer_name,"currency":record.currency,"subtotal":record.subtotal,"discount":record.discount,"tax_rate":record.tax_rate,"tax_amount":record.tax_amount,"total_amount":record.total_amount,"status":record.status.value,"duplicate_status":record.duplicate_status,"duplicate_score":record.duplicate_score,"anomaly_count":len(record.anomaly_alerts),"source_file":record.source_file}

def export_json(records: list[InvoiceRecord], path: str | Path) -> None:
    Path(path).write_text(json.dumps([r.to_dict() for r in records], indent=2, ensure_ascii=False), encoding="utf-8")

def export_csv(records: list[InvoiceRecord], path: str | Path) -> None:
    rows=[_summary(r) for r in records]
    with Path(path).open("w", newline="", encoding="utf-8-sig") as f:
        writer=csv.DictWriter(f, fieldnames=list(rows[0]) if rows else list(_summary(InvoiceRecord()).keys())); writer.writeheader(); writer.writerows(rows)

def export_excel(records: list[InvoiceRecord], path: str | Path) -> None:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill
    wb=Workbook(); summary=wb.active; summary.title="Invoice Summary"
    rows=[_summary(r) for r in records]; fields=list(rows[0]) if rows else list(_summary(InvoiceRecord()).keys())
    summary.append(fields)
    for row in rows: summary.append([row.get(k) for k in fields])
    items=wb.create_sheet("Line Items"); item_fields=["source_file","invoice_number","description","quantity","unit","unit_price","discount","tax_rate","tax_amount","total","sku","hsn_sac"]
    items.append(item_fields)
    for r in records:
        for item in r.line_items: items.append([r.source_file,r.invoice_number,item.description,item.quantity,item.unit,item.unit_price,item.discount,item.tax_rate,item.tax_amount,item.total,item.sku,item.hsn_sac])
    issues=wb.create_sheet("Processing Issues"); issue_fields=["source_file","invoice_number","status","code","severity","field","message","context"]; issues.append(issue_fields)
    for r in records:
        for i in r.issues: issues.append([r.source_file,r.invoice_number,r.status.value,i.code,i.severity,i.field,i.message,i.context])
        for alert in r.anomaly_alerts: issues.append([r.source_file,r.invoice_number,r.status.value,alert.code,alert.severity,alert.field,alert.message,alert.expected])
    for ws in wb.worksheets:
        ws.freeze_panes="A2"; ws.auto_filter.ref=ws.dimensions
        for cell in ws[1]: cell.font=Font(bold=True,color="FFFFFF"); cell.fill=PatternFill("solid",fgColor="263238")
        for column in ws.columns:
            letter=column[0].column_letter; ws.column_dimensions[letter].width=min(48,max(12,max(len(str(c.value or "")) for c in column)+2))
    wb.save(path)
