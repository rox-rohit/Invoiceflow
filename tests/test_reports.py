from datetime import date
from src.financials import FinancialTransaction
from src.report_config import ReportConfigStore, SavedReportConfig
from src.report_exporter import export_report_csv, export_report_excel, export_report_json
from src.reports import build_report, period_for, target_scenarios

def tx(day,kind,amount,party="",source=1): return FinancialTransaction(day,kind,amount,"INR",source,f"{source}.pdf",True,party=party)

def test_monthly_report_has_traceable_metrics_and_insight(tmp_path):
    current=[tx("2026-01-05","sale",1000,source=1),tx("2026-01-10","purchase",700,"Supplier A",2),tx("2026-01-20","expense",100,"Rent",3),tx("2026-01-25","collection",500,source=4)]
    previous=[tx("2025-12-05","sale",800,source=5),tx("2025-12-10","purchase",300,"Supplier A",6)]
    report=build_report(current+previous,period_for("month",date(2026,1,15)),"INR",period_for("month",date(2025,12,15)),budgets={"expense":80})
    assert report.metrics["sale"].value==1000 and report.metrics["estimated_net_profit"].value==200
    assert report.metrics["sale"].source_ids==[1] and report.insights
    scenarios=target_scenarios(report,sales_target=1500); assert scenarios["expected"]["required_sales"]>=0

def test_report_exports_and_saved_config(tmp_path):
    report=build_report([tx("2026-01-01","sale",100,"",1)],period_for("month",date(2026,1,15)),"INR")
    export_report_json(report,tmp_path/"r.json"); export_report_csv(report,tmp_path/"r.csv"); export_report_excel(report,tmp_path/"r.xlsx")
    store=ReportConfigStore(tmp_path/"reports.json"); store.save(SavedReportConfig("Monthly",currency="INR")); assert store.load()[0].name=="Monthly"
    assert (tmp_path/"r.json").exists() and (tmp_path/"r.xlsx").exists()
