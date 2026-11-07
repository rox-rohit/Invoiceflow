from datetime import date
from decimal import Decimal

from src.analytics import build_analytics
from src.ledger import LedgerTransaction
from src.reports import period_for


def transaction(kind, day, amount, category="", party=""):
    return LedgerTransaction(transaction_type=kind, transaction_date=day, amount=amount, currency="INR", category=category, counterparty=party, verification_status="VERIFIED")


def test_analytics_uses_verified_financial_concepts_and_source_data():
    period = period_for("month", date(2026, 1, 15))
    items = [transaction("sale", "2026-01-02", "1000", party="Customer"), transaction("sales_return", "2026-01-03", "100"), transaction("purchase", "2026-01-04", "500", party="Supplier"), transaction("expense", "2026-01-05", "100", category="Rent"), transaction("collection", "2026-01-06", "400"), transaction("supplier_payment", "2026-01-07", "250")]
    snapshot = build_analytics(items, period, "INR")
    assert snapshot.kpis["sales"]["value"] == Decimal("900.00")
    assert snapshot.kpis["gross_profit"]["value"] == Decimal("400.00")
    assert snapshot.kpis["net_profit"]["value"] == Decimal("300.00")
    assert snapshot.kpis["collections"]["value"] == Decimal("400.00")
    assert snapshot.kpis["payments"]["value"] == Decimal("250.00")
    assert snapshot.expense_categories[0]["category"] == "Rent"
    assert snapshot.customers[0]["name"] == "Customer"
    assert snapshot.suppliers[0]["name"] == "Supplier"


def test_net_profit_is_not_presented_without_expense_data():
    period = period_for("month", date(2026, 1, 15))
    snapshot = build_analytics([transaction("sale", "2026-01-02", "1000"), transaction("purchase", "2026-01-03", "500")], period, "INR")
    assert snapshot.kpis["gross_profit"]["value"] == Decimal("500.00")
    assert snapshot.kpis["net_profit"]["value"] is None
    assert any("operating-expense" in reason for reason in snapshot.data_quality)

def test_monthly_series_has_stable_columns_when_types_are_missing():
    period = period_for("month", date(2026, 1, 15))
    snapshot = build_analytics([transaction("sale", "2026-01-02", "1000")], period, "INR")
    assert set(("sales", "purchases", "expenses", "collections", "payments")).issubset(snapshot.monthly[0])


def test_extended_periods_and_invalid_custom_range():
    assert period_for("last_month", date(2026, 3, 15)).start == date(2026, 2, 1)
    assert period_for("current_financial_year", date(2026, 3, 15)).start == date(2025, 4, 1)
    assert period_for("previous_financial_year", date(2026, 5, 15)).start == date(2025, 4, 1)


def test_series_uses_daily_buckets_for_single_day_and_separates_cash():
    period = period_for("day", date(2026, 11, 7))
    items = [
        transaction("sale", "2026-11-07", "50000"),
        transaction("purchase", "2026-11-07", "2000"),
        transaction("collection", "2026-11-07", "10000"),
        transaction("supplier_payment", "2026-11-07", "500"),
    ]
    snapshot = build_analytics(items, period, "INR")
    assert snapshot.granularity == "day"
    assert len(snapshot.series) == 1
    assert snapshot.series[0]["sales"] == Decimal("50000.00")
    assert snapshot.series[0]["purchases"] == Decimal("2000.00")
    assert snapshot.series[0]["expenses"] == Decimal("0.00")
    assert snapshot.series[0]["collections"] == Decimal("10000.00")
    assert snapshot.series[0]["payments"] == Decimal("500.00")


def test_series_uses_weekly_and_monthly_buckets_for_longer_periods():
    weekly = build_analytics(
        [transaction("sale", "2026-01-02", "100"), transaction("sale", "2026-02-01", "200")],
        period_for("last_3_months", date(2026, 2, 15)),
        "INR",
    )
    annual = build_analytics(
        [transaction("sale", "2026-01-02", "100"), transaction("sale", "2026-02-01", "200")],
        period_for("last_12_months", date(2026, 2, 15)),
        "INR",
    )
    assert weekly.granularity == "week"
    assert annual.granularity == "month"
    assert sum((row["sales"] for row in weekly.series), Decimal("0.00")) == Decimal("300.00")
    assert sum((row["sales"] for row in annual.series), Decimal("0.00")) == Decimal("300.00")


def test_budget_utilization_is_period_scoped_and_excludes_reversed_expenses():
    period = period_for("month", date(2026, 1, 15))
    items = [
        transaction("expense", "2026-01-05", "900", category="Rent"),
        transaction("expense", "2026-01-06", "250", category="Rent"),
        LedgerTransaction(
            transaction_type="expense",
            transaction_date="2026-01-07",
            amount="500",
            currency="INR",
            category="Rent",
            verification_status="REVERSED",
        ),
    ]
    snapshot = build_analytics(
        items,
        period,
        budgets=[{
            "budget_id": 1,
            "period_start": "2026-01-01",
            "period_end": "2026-01-31",
            "category": "Rent",
            "amount": "1000",
            "currency": "INR",
            "active": 1,
        }],
    )
    row = snapshot.budget_utilization[0]
    assert row["budget"] == Decimal("1000.00")
    assert row["actual"] == Decimal("1150.00")
    assert row["remaining"] == Decimal("-150.00")
    assert row["overspent"] is True
    assert row["utilization"] == Decimal("1.15")
