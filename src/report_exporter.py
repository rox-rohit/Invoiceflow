from __future__ import annotations
import csv, json
from pathlib import Path
from .reports import BusinessReport

def export_report_json(report: BusinessReport, destination: str | Path) -> Path:
    destination=Path(destination); destination.write_text(json.dumps(report.to_dict(),indent=2,ensure_ascii=False),encoding="utf-8"); return destination

def export_report_csv(report: BusinessReport, destination: str | Path) -> Path:
    destination=Path(destination); destination.parent.mkdir(parents=True,exist_ok=True)
    with destination.open("w",newline="",encoding="utf-8-sig") as stream:
        writer=csv.writer(stream); writer.writerow(["InvoiceFlow Business Report",report.period.label]); writer.writerow(["Metric","Value","Currency","Complete","Estimated","Explanation"])
        for metric in report.metrics.values(): writer.writerow([metric.name,metric.value,metric.currency,metric.complete,metric.estimated,metric.explanation])
        writer.writerow([]); writer.writerow(["Monthly breakdown"]); writer.writerow(["Month","Sales","Purchases","Expenses","Estimated Profit","Collections","Payments"])
        for row in report.monthly_breakdown: writer.writerow([row.get(k) for k in ("month","sales","purchases","expenses","estimated_profit","collections","payments")])
        writer.writerow([]); writer.writerow(["Insights"]); writer.writerow(["Finding","Impact","Suggested action","Confidence"])
        for insight in report.insights: writer.writerow([insight.finding,insight.business_impact,insight.suggested_action,insight.confidence])
    return destination

def export_report_excel(report: BusinessReport, destination: str | Path) -> Path:
    from openpyxl import Workbook
    from openpyxl.styles import Font
    destination=Path(destination); destination.parent.mkdir(parents=True,exist_ok=True); workbook=Workbook(); summary=workbook.active; summary.title="Summary"; summary.append(["Metric","Value","Currency","Complete","Estimated","Explanation"])
    for metric in report.metrics.values(): summary.append([metric.name,metric.value,metric.currency,metric.complete,metric.estimated,metric.explanation])
    monthly=workbook.create_sheet("Monthly"); monthly.append(["Month","Sales","Purchases","Expenses","Estimated Profit","Collections","Payments"])
    for row in report.monthly_breakdown: monthly.append([row.get(k) for k in ("month","sales","purchases","expenses","estimated_profit","collections","payments")])
    insights=workbook.create_sheet("Insights"); insights.append(["Finding","Figures","Source IDs","Impact","Suggested Action","Confidence","Complete"])
    for item in report.insights: insights.append([item.finding,json.dumps(item.supporting_figures),json.dumps(item.source_ids),item.business_impact,item.suggested_action,item.confidence,item.data_complete])
    for sheet in workbook.worksheets:
        sheet.freeze_panes="A2"; sheet.auto_filter.ref=sheet.dimensions
        for cell in sheet[1]: cell.font=Font(bold=True)
    workbook.save(destination); return destination
