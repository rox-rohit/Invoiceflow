"""Measure analytics-service performance on synthetic transaction volumes."""
from __future__ import annotations

import json
import sys
import time
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.analytics import build_analytics
from src.ledger import LedgerTransaction
from src.reports import period_for


def main():
    period = period_for("last_12_months", date(2026, 12, 15))
    output = []
    for size in (1000, 10000, 50000):
        items = [LedgerTransaction(transaction_type="sale" if index % 3 == 0 else "expense", transaction_date=f"2026-{index % 12 + 1:02d}-{index % 28 + 1:02d}", amount="100.00", currency="INR", category="Utilities", verification_status="VERIFIED") for index in range(size)]
        started = time.perf_counter(); snapshot = build_analytics(items, period, "INR"); elapsed = time.perf_counter() - started
        output.append({"transactions": size, "seconds": round(elapsed, 4), "kpis": len(snapshot.kpis), "monthly_rows": len(snapshot.monthly)})
    print(json.dumps(output, indent=2))


if __name__ == "__main__": main()
