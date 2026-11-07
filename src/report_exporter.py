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

def export_report_pdf(report: BusinessReport, destination: str | Path) -> Path:
    """Create a compact shareable report with explicit data-quality disclosures."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    destination=Path(destination); destination.parent.mkdir(parents=True,exist_ok=True)
    styles=getSampleStyleSheet(); document=SimpleDocTemplate(str(destination),pagesize=A4,rightMargin=16*mm,leftMargin=16*mm,topMargin=16*mm,bottomMargin=16*mm)
    story=[Paragraph("InvoiceFlow Business Report",styles["Title"]),Paragraph(f"{report.period.label} · {report.period.start.isoformat()} to {report.period.end.isoformat()} · {report.currency}",styles["Normal"]),Spacer(1,8)]
    rows=[["Metric","Value","Status","Explanation"]]
    for metric in report.metrics.values(): rows.append([metric.name,"Unavailable" if metric.value is None else f"{metric.value:,.2f} {metric.currency}","Estimated" if metric.estimated else "Verified",metric.explanation])
    table=Table(rows,colWidths=[35*mm,30*mm,24*mm,90*mm],repeatRows=1); table.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#1976d2")),("TEXTCOLOR",(0,0),(-1,0),colors.white),("GRID",(0,0),(-1,-1),0.25,colors.HexColor("#dce3e7")),("VALIGN",(0,0),(-1,-1),"TOP"),("FONTSIZE",(0,0),(-1,-1),8)])); story.append(table)
    if report.data_quality: story.extend([Spacer(1,8),Paragraph("Data completeness",styles["Heading2"]),Paragraph("<br/>".join(report.data_quality),styles["BodyText"])])
    if report.insights:
        story.extend([Spacer(1,8),Paragraph("Business insights",styles["Heading2"])])
        for insight in report.insights: story.append(Paragraph(f"{insight.finding} — {insight.suggested_action}",styles["BodyText"]))
    document.build(story); return destination
