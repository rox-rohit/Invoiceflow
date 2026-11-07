from src.financials import budget_variance, summarize, transactions_from_invoices
from src.models import InvoiceRecord

def test_financial_summary_does_not_treat_invoice_as_cash():
    record=InvoiceRecord(record_id=1,source_file="a.pdf",invoice_date="2026-01-01",currency="INR",total_amount=100)
    tx=transactions_from_invoices([record],{1:"sale"}); summary=summarize(tx,"INR")
    assert summary.sales==100 and summary.collections==0 and summary.estimated is True

def test_budget_variance():
    result=budget_variance(11000,8000); assert result["overspent"] and result["remaining"]==-3000
