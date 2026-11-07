from __future__ import annotations
from dataclasses import dataclass, asdict
from collections import defaultdict
from datetime import date
from .models import InvoiceRecord

@dataclass
class FinancialTransaction:
    transaction_date: str
    kind: str  # sale, purchase, expense, collection, payment
    amount: float
    currency: str
    source_record_id: int | None = None
    source_file: str = ""
    verified: bool = False
    category: str = ""
    party: str = ""
    product: str = ""
    payment_status: str = "unknown"

@dataclass
class FinancialSummary:
    currency: str
    sales: float = 0.0
    purchases: float = 0.0
    expenses: float = 0.0
    collections: float = 0.0
    payments: float = 0.0
    estimated: bool = True
    incomplete_reasons: list[str] | None = None
    def to_dict(self): return asdict(self)

def transactions_from_invoices(records: list[InvoiceRecord], explicit_kinds: dict[int | str, str]) -> list[FinancialTransaction]:
    """Create transactions only from an explicit user/import classification; invoice type is not treated as cash payment."""
    transactions=[]
    for record in records:
        kind=explicit_kinds.get(record.record_id) or explicit_kinds.get(record.source_file)
        if kind not in {"sale","purchase","expense","collection","payment"}: continue
        amount=record.total_amount
        if amount is not None:
            party=record.vendor_name if kind in {"purchase","payment"} else record.customer_name
            transactions.append(FinancialTransaction(record.invoice_date or "",kind,amount,record.currency,record.record_id,record.source_file,False,category=record.document_type,party=party,payment_status="unknown"))
    return transactions

def summarize(transactions: list[FinancialTransaction], currency: str) -> FinancialSummary:
    result=FinancialSummary(currency,incomplete_reasons=[]); result.estimated=True
    for transaction in transactions:
        if transaction.currency and transaction.currency!=currency: continue
        if transaction.kind=="sale": result.sales+=transaction.amount
        elif transaction.kind=="purchase": result.purchases+=transaction.amount
        elif transaction.kind=="expense": result.expenses+=transaction.amount
        elif transaction.kind=="collection": result.collections+=transaction.amount
        elif transaction.kind=="payment": result.payments+=transaction.amount
    result.incomplete_reasons=["Invoice documents do not prove cash collection or payment.","Cost of goods sold, opening balances and inventory movements are not available unless explicitly imported."]
    return result

def budget_variance(actual: float, budget: float, warning_threshold: float=0.9) -> dict:
    utilization=(actual/budget) if budget else None
    return {"actual":actual,"budget":budget,"remaining":budget-actual,"utilization":utilization,"overspent":actual>budget,"warning":utilization is not None and utilization>=warning_threshold}
