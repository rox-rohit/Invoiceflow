from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable

from .ledger import LedgerTransaction, money
from .reports import ReportPeriod


ZERO = Decimal("0.00")


def _amount(value) -> Decimal:
    return value if isinstance(value, Decimal) else Decimal(str(value or 0))


def _source(transaction):
    return transaction.transaction_id or transaction.source_record_id or transaction.source_file


def _kind(transaction):
    return getattr(transaction, "transaction_type", getattr(transaction, "kind", ""))


def _party(transaction):
    return getattr(transaction, "counterparty", getattr(transaction, "party", "")) or "Unassigned"


@dataclass
class AnalyticsSnapshot:
    period: ReportPeriod
    currency: str
    kpis: dict
    monthly: list[dict]
    expense_categories: list[dict]
    customers: list[dict]
    suppliers: list[dict]
    insights: list[dict]
    data_quality: list[str]
    transactions: list[LedgerTransaction]


def _in_period(transaction, period: ReportPeriod, currency: str) -> bool:
    return period.contains(getattr(transaction, "transaction_date", "")) and (not transaction.currency or transaction.currency == currency)


def _totals(transactions: list[LedgerTransaction]) -> dict[str, Decimal]:
    totals = defaultdict(lambda: ZERO)
    for transaction in transactions:
        amount = _amount(transaction.amount)
        kind = _kind(transaction)
        if kind == "sale": totals["sales"] += amount
        elif kind == "sales_return": totals["sales"] -= amount
        elif kind == "purchase": totals["purchases"] += amount
        elif kind == "purchase_return": totals["purchases"] -= amount
        elif kind == "expense": totals["expenses"] += amount
        elif kind == "collection": totals["collections"] += amount
        elif kind in {"payment", "supplier_payment"}: totals["payments"] += amount
    return totals


def _metric(value, source_ids, explanation, complete=True, estimated=False, previous=None):
    change = None
    if previous not in (None, ZERO):
        change = (value - previous) / previous
    return {"value": value, "source_ids": source_ids, "explanation": explanation, "complete": complete, "estimated": estimated, "previous": previous, "change": change}


def build_analytics(transactions: Iterable[LedgerTransaction], period: ReportPeriod, currency: str = "INR", previous_period: ReportPeriod | None = None, budgets: dict[str, Decimal | float | str] | None = None) -> AnalyticsSnapshot:
    all_transactions = list(transactions)
    current = [item for item in all_transactions if _in_period(item, period, currency)]
    previous = [item for item in all_transactions if previous_period and _in_period(item, previous_period, currency)]
    totals = _totals(current)
    previous_totals = _totals(previous)
    ids = {name: [_source(item) for item in current if ((name == "sales" and _kind(item) in {"sale", "sales_return"}) or (name == "purchases" and _kind(item) in {"purchase", "purchase_return"}) or (name == "expenses" and _kind(item) == "expense") or (name == "collections" and _kind(item) == "collection") or (name == "payments" and _kind(item) in {"payment", "supplier_payment"}))] for name in ("sales", "purchases", "expenses", "collections", "payments")}
    quality = []
    sales = totals["sales"]
    purchases = totals["purchases"]
    expenses = totals["expenses"]
    gross_profit = sales - purchases if sales and purchases else None
    net_profit = gross_profit - expenses if gross_profit is not None and expenses else None
    if not current: quality.append("No verified transactions exist in the selected period.")
    if not purchases: quality.append("Gross profit is unavailable because verified purchase or inventory-cost records are missing.")
    if not expenses: quality.append("Net profit is unavailable because verified operating-expense records are missing.")
    if any(item.currency and item.currency != currency for item in all_transactions): quality.append("Transactions in other currencies were excluded because no exchange rate was supplied.")
    kpis = {
        "sales": _metric(sales, ids["sales"], "Verified sales less verified sales returns.", previous=previous_totals["sales"]),
        "purchases": _metric(purchases, ids["purchases"], "Verified purchases less verified purchase returns.", previous=previous_totals["purchases"]),
        "expenses": _metric(expenses, ids["expenses"], "Verified operating expenses.", previous=previous_totals["expenses"]),
        "gross_profit": _metric(gross_profit, ids["sales"] + ids["purchases"], "Sales less purchases; inventory opening and closing balances are not included.", gross_profit is not None, True, previous_totals["sales"] - previous_totals["purchases"] if previous_totals["purchases"] else None),
        "net_profit": _metric(net_profit, ids["sales"] + ids["purchases"] + ids["expenses"], "Estimated gross profit less verified operating expenses.", net_profit is not None, True, previous_totals["sales"] - previous_totals["purchases"] - previous_totals["expenses"] if previous_totals["purchases"] and previous_totals["expenses"] else None),
        "collections": _metric(totals["collections"], ids["collections"], "Explicitly recorded customer collections; sales invoices are not treated as cash received.", previous=previous_totals["collections"]),
        "payments": _metric(totals["payments"], ids["payments"], "Explicitly recorded supplier and operating payments; purchases are not treated as cash paid.", previous=previous_totals["payments"]),
        "transaction_count": _metric(Decimal(len(current)), [_source(item) for item in current], "Verified transactions in the selected period.", True, False, Decimal(len(previous))),
    }
    monthly = defaultdict(lambda: defaultdict(lambda: ZERO))
    for item in current:
        month = item.transaction_date[:7]
        kind = _kind(item); amount = _amount(item.amount)
        if kind in {"sale", "sales_return"}: monthly[month]["sales"] += amount if kind == "sale" else -amount
        elif kind in {"purchase", "purchase_return"}: monthly[month]["purchases"] += amount if kind == "purchase" else -amount
        elif kind == "expense": monthly[month]["expenses"] += amount
        elif kind == "collection": monthly[month]["collections"] += amount
        elif kind in {"payment", "supplier_payment"}: monthly[month]["payments"] += amount
    monthly_rows = []
    for month in sorted(monthly):
        row = dict(month=month, sales=monthly[month]["sales"], purchases=monthly[month]["purchases"], expenses=monthly[month]["expenses"], collections=monthly[month]["collections"], payments=monthly[month]["payments"]); row["gross_profit"] = row["sales"] - row["purchases"] if row["purchases"] else None; monthly_rows.append(row)
    category_totals = defaultdict(lambda: ZERO); category_ids = defaultdict(list)
    for item in current:
        if _kind(item) == "expense": category_totals[item.category or "Uncategorized"] += _amount(item.amount); category_ids[item.category or "Uncategorized"].append(_source(item))
    expense_categories = [dict(category=key, amount=value, source_ids=category_ids[key]) for key, value in sorted(category_totals.items(), key=lambda pair: pair[1], reverse=True)]
    party_sales = defaultdict(lambda: ZERO); party_purchases = defaultdict(lambda: ZERO); party_ids = defaultdict(list)
    for item in current:
        if _kind(item) in {"sale", "sales_return"}: party_sales[_party(item)] += _amount(item.amount) * (1 if _kind(item) == "sale" else -1); party_ids[_party(item)].append(_source(item))
        if _kind(item) in {"purchase", "purchase_return"}: party_purchases[_party(item)] += _amount(item.amount) * (1 if _kind(item) == "purchase" else -1); party_ids[_party(item)].append(_source(item))
    customers = [dict(name=key, amount=value, source_ids=party_ids[key]) for key, value in sorted(party_sales.items(), key=lambda pair: pair[1], reverse=True)]
    suppliers = [dict(name=key, amount=value, source_ids=party_ids[key]) for key, value in sorted(party_purchases.items(), key=lambda pair: pair[1], reverse=True)]
    insights = []
    if previous_period and previous_totals["sales"] and sales < previous_totals["sales"]:
        insights.append(dict(finding="Sales decreased compared with the previous period.", evidence={"current": sales, "previous": previous_totals["sales"]}, source_ids=ids["sales"], action="Review the largest customer and product changes.", confidence="medium"))
    if previous_period and previous_totals["expenses"] and expenses > previous_totals["expenses"] * Decimal("1.2"):
        insights.append(dict(finding="Operating expenses increased by more than 20%.", evidence={"current": expenses, "previous": previous_totals["expenses"]}, source_ids=ids["expenses"], action="Review the largest expense categories and linked source records.", confidence="high"))
    if budgets:
        for category, planned in budgets.items():
            actual = category_totals.get(category, ZERO); planned_amount = money(planned)
            if planned_amount and actual > planned_amount: insights.append(dict(finding=f"{category} is over budget.", evidence={"actual": actual, "budget": planned_amount, "overspend": actual - planned_amount}, source_ids=category_ids.get(category, []), action="Review the linked expenses and update the spending plan if appropriate.", confidence="high"))
    return AnalyticsSnapshot(period, currency, kpis, monthly_rows, expense_categories, customers, suppliers, insights, quality, current)
