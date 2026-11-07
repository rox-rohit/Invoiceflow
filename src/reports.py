from __future__ import annotations
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta
from statistics import median
from decimal import Decimal
from typing import Iterable
from .financials import FinancialTransaction

@dataclass(frozen=True)
class ReportPeriod:
    start: date
    end: date
    label: str
    complete: bool = True
    def contains(self, value: str) -> bool:
        try: parsed=date.fromisoformat(value[:10])
        except (TypeError,ValueError): return False
        return self.start <= parsed <= self.end

@dataclass
class ReportMetric:
    name: str
    value: float | None
    currency: str
    source_ids: list[int | str] = field(default_factory=list)
    complete: bool = True
    estimated: bool = True
    explanation: str = ""

@dataclass
class BusinessInsight:
    finding: str
    supporting_figures: dict[str,float | str]
    source_ids: list[int | str]
    comparison_period: str
    business_impact: str
    suggested_action: str
    confidence: str
    data_complete: bool

@dataclass
class BusinessReport:
    period: ReportPeriod
    currency: str
    metrics: dict[str,ReportMetric]
    monthly_breakdown: list[dict]
    insights: list[BusinessInsight]
    health_components: dict[str,dict]
    data_quality: list[str]
    filters: dict = field(default_factory=dict)
    generated_at: str = field(default_factory=lambda:datetime.now().isoformat(timespec="seconds"))
    def to_dict(self):
        data=asdict(self); data["period"]["start"]=self.period.start.isoformat(); data["period"]["end"]=self.period.end.isoformat()
        # Decimal is retained throughout calculations; JSON has no decimal type.
        # Convert only at the export boundary so report files remain interoperable.
        def json_value(value):
            if isinstance(value, Decimal): return float(value)
            if isinstance(value, dict): return {key: json_value(item) for key,item in value.items()}
            if isinstance(value, list): return [json_value(item) for item in value]
            return value
        return json_value(data)

def period_between(start: date, end: date, label: str = "Custom period") -> ReportPeriod:
    if end < start: raise ValueError("Report end date cannot be before its start date")
    return ReportPeriod(start, end, label, end <= date.today())

def previous_period(period: ReportPeriod) -> ReportPeriod:
    length = (period.end - period.start).days + 1
    end = period.start - timedelta(days=1)
    return ReportPeriod(end - timedelta(days=length - 1), end, "Previous " + period.label, end <= date.today())

def period_for(kind: str, anchor: date | None=None, financial_year_start_month: int = 4) -> ReportPeriod:
    anchor=anchor or date.today(); first=anchor.replace(day=1); next_month=(first.replace(day=28)+timedelta(days=4)).replace(day=1); month_end=next_month-timedelta(days=1)
    if kind=="day": return ReportPeriod(anchor,anchor,anchor.isoformat())
    if kind=="week":
        start=anchor-timedelta(days=anchor.weekday()); return ReportPeriod(start,start+timedelta(days=6),f"Week of {start.isoformat()}")
    if kind=="yesterday": return ReportPeriod(anchor-timedelta(days=1),anchor-timedelta(days=1),"Yesterday")
    if kind=="last_week":
        end=anchor-timedelta(days=anchor.weekday()+1); return ReportPeriod(end-timedelta(days=6),end,"Last week")
    if kind=="month": return ReportPeriod(first,month_end,first.strftime("%B %Y"),month_end<=date.today())
    if kind=="last_month":
        end=first-timedelta(days=1); start=end.replace(day=1); return ReportPeriod(start,end,start.strftime("%B %Y"),end<=date.today())
    if kind in {"last_3_months","last_6_months","last_12_months"}:
        count={"last_3_months":3,"last_6_months":6,"last_12_months":12}[kind]; start=first
        for _ in range(count-1): start=(start.replace(day=1)-timedelta(days=1)).replace(day=1)
        return ReportPeriod(start,month_end, f"Last {count} months", month_end<=date.today())
    if kind=="year_to_date": return ReportPeriod(anchor.replace(month=1,day=1),anchor,"Year to date",False)
    if kind=="calendar_year": return ReportPeriod(anchor.replace(month=1,day=1),anchor.replace(month=12,day=31),str(anchor.year),anchor<date(anchor.year,12,31))
    if kind in {"current_financial_year","previous_financial_year"}:
        year=anchor.year if anchor.month >= financial_year_start_month else anchor.year-1
        if kind=="previous_financial_year": year-=1
        start=date(year,financial_year_start_month,1); end=date(year+1,financial_year_start_month,1)-timedelta(days=1)
        return ReportPeriod(start,end,f"Financial year {year}-{str(year+1)[-2:]}",end<=date.today())
    raise ValueError(f"Unsupported report period: {kind}")

def _amount(value) -> Decimal:
    return value if isinstance(value,Decimal) else Decimal(str(value or 0))

def _zero() -> Decimal:
    return Decimal("0.00")

def _kind(tx): return getattr(tx,"kind",getattr(tx,"transaction_type",""))
def _party(tx): return getattr(tx,"party",getattr(tx,"counterparty",""))
def _source(tx): return getattr(tx,"source_record_id",None) or getattr(tx,"source_file","")

def _metric(name, transactions, kind, currency):
    selected=[t for t in transactions if _kind(t)==kind and (not t.currency or t.currency==currency)]; return ReportMetric(name,sum((_amount(t.amount) for t in selected),Decimal("0.00")),currency,[_source(t) for t in selected],True,True,f"Based on explicitly classified {kind} transactions.")

def build_report(transactions: Iterable[FinancialTransaction], period: ReportPeriod, currency: str, previous_period: ReportPeriod | None=None, budgets: dict[str,float] | None=None, filters: dict | None=None) -> BusinessReport:
    all_tx=list(transactions); quality=[]
    current=[t for t in all_tx if period.contains(t.transaction_date) and (not t.currency or t.currency==currency)]
    if any(t.currency and t.currency!=currency for t in all_tx): quality.append("Transactions in other currencies were excluded; no exchange rate was supplied.")
    if not current: quality.append("No classified transactions exist in the selected period.")
    metrics={kind:_metric(label,current,kind,currency) for kind,label in (("sale","Gross sales"),("purchase","Purchase costs"),("expense","Operating expenses"),("collection","Customer collections"),("payment","Supplier payments"))}
    sales=metrics["sale"].value or _zero(); purchases=metrics["purchase"].value or _zero(); expenses=metrics["expense"].value or _zero()
    metrics["gross_profit"]=ReportMetric("Estimated gross profit",sales-purchases,currency,metrics["sale"].source_ids+metrics["purchase"].source_ids,False,True,"Sales minus explicitly classified purchases; inventory movements are not available.")
    metrics["estimated_net_profit"]=ReportMetric("Estimated net profit",sales-purchases-expenses,currency,metrics["sale"].source_ids+metrics["purchase"].source_ids+metrics["expense"].source_ids,False,True,"Estimated as sales minus purchases and operating expenses; accruals and inventory are incomplete.")
    months=defaultdict(lambda:defaultdict(lambda:Decimal("0.00")))
    for tx in current:
        if len(tx.transaction_date)>=7: months[tx.transaction_date[:7]][_kind(tx)]+=_amount(tx.amount)
    breakdown=[]
    for month in sorted(months):
        row=dict(month=month,sales=months[month]["sale"],purchases=months[month]["purchase"],expenses=months[month]["expense"],collections=months[month]["collection"],payments=months[month]["payment"]); row["estimated_profit"]=row["sales"]-row["purchases"]-row["expenses"]; breakdown.append(row)
    insights=[]; previous=[]
    if previous_period: previous=[t for t in all_tx if previous_period.contains(t.transaction_date) and (not t.currency or t.currency==currency)]
    previous_sales=sum((_amount(t.amount) for t in previous if _kind(t)=="sale"),Decimal("0.00")); current_profit=metrics["estimated_net_profit"].value or Decimal("0.00")
    previous_profit=previous_sales-sum((_amount(t.amount) for t in previous if _kind(t)=="purchase"),Decimal("0.00"))-sum((_amount(t.amount) for t in previous if _kind(t)=="expense"),Decimal("0.00"))
    if previous_period and sales>previous_sales and current_profit<previous_profit:
        ids=metrics["sale"].source_ids+metrics["purchase"].source_ids; insights.append(BusinessInsight("Sales increased while estimated profit decreased",{"sales":sales,"previous_sales":previous_sales,"estimated_profit":current_profit,"previous_profit":previous_profit},ids,previous_period.label,"Growth is not translating into estimated profit.","Review purchase costs, discounts and operating expenses.","medium",False))
    if budgets:
        for kind,budget in budgets.items():
            actual=metrics.get(kind,ReportMetric(kind,_zero(),currency)).value or _zero(); budget_amount=_amount(budget)
            if budget_amount and actual>budget_amount:
                ids=metrics.get(kind,ReportMetric(kind,_zero(),currency)).source_ids; insights.append(BusinessInsight(f"{kind.title()} exceed the configured budget",{"actual":actual,"budget":budget_amount,"overspend":actual-budget_amount},ids,period.label,"The recorded amount is above the planned limit.","Review the linked source records and update the budget or spending plan.","high",True))
    supplier_totals=defaultdict(lambda:Decimal("0.00")); supplier_ids=defaultdict(list)
    for tx in current:
        if _kind(tx)=="purchase" and _party(tx): supplier_totals[_party(tx)]+=_amount(tx.amount); supplier_ids[_party(tx)].append(_source(tx))
    if purchases and supplier_totals:
        supplier,amount=max(supplier_totals.items(),key=lambda pair:pair[1]); share=amount/purchases
        if share>=0.7: insights.append(BusinessInsight("Purchases are concentrated with one supplier",{"supplier":supplier,"share":share,"amount":amount},supplier_ids[supplier],period.label,"Supplier dependency may increase price and continuity risk.","Compare supplier prices and review alternatives.","medium",True))
    health={
        "revenue_growth":{"value":None if not previous_period or previous_sales==0 else (sales-previous_sales)/previous_sales,"complete":bool(previous_period and previous_sales),"explanation":"Compared with the selected previous period."},
        "profitability":{"value":None if sales==0 else current_profit/sales,"complete":sales>0,"explanation":"Estimated profit margin; inventory and accrual data may be incomplete."},
        "cash_flow":{"value":(metrics["collection"].value or _zero())-(metrics["payment"].value or _zero()),"complete":True,"explanation":"Based only on explicitly imported collection/payment transactions."},
        "data_completeness":{"value":0.0 if not current else 1.0,"complete":bool(current),"explanation":"This reflects classified records in the period, not accounting completeness."},
    }
    if not current: quality.append("Sales, costs, payments and profit are unavailable until transactions are classified or imported.")
    return BusinessReport(period,currency,metrics,breakdown,insights,health,quality,filters or {})

def target_scenarios(report: BusinessReport, sales_target: float | None=None, profit_target: float | None=None) -> dict:
    days=max(1,(report.period.end-report.period.start).days+1); elapsed=max(1,min(days,(date.today()-report.period.start).days+1)); sales=report.metrics.get("sale",ReportMetric("",_zero(),report.currency)).value or _zero(); profit=report.metrics.get("estimated_net_profit",ReportMetric("",_zero(),report.currency)).value or _zero(); result={}
    for name,multiplier in (("conservative",Decimal("0.8")),("expected",Decimal("1.0")),("optimistic",Decimal("1.2"))):
        sales_target_amount=None if sales_target is None else _amount(sales_target); profit_target_amount=None if profit_target is None else _amount(profit_target)
        projected_sales=sales/elapsed*days*multiplier; projected_profit=profit/elapsed*days*multiplier; result[name]={"projected_sales":projected_sales,"projected_profit":projected_profit,"required_sales":None if sales_target_amount is None else max(_zero(),sales_target_amount-projected_sales),"required_profit":None if profit_target_amount is None else max(_zero(),profit_target_amount-projected_profit)}
    return result
