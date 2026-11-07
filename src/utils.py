from __future__ import annotations
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation

DATE_PATTERNS = ["%d/%m/%Y", "%m/%d/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d.%m.%Y", "%d %b %Y", "%d %B %Y", "%b %d, %Y", "%B %d, %Y"]

def normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()

def parse_amount(value: str | None) -> float | None:
    if not value:
        return None
    raw = value.replace("₹", "").replace("$", "").replace("€", "").replace("£", "")
    raw = re.sub(r"[^0-9,.(+\-]", "", raw).strip()
    if not raw or raw in {"-", "+", "."}:
        return None
    negative = raw.startswith("(") and raw.endswith(")")
    raw = raw.strip("()")
    if "," in raw and "." in raw:
        raw = raw.replace(",", "") if raw.rfind(".") > raw.rfind(",") else raw.replace(".", "").replace(",", ".")
    elif raw.count(",") == 1 and len(raw.split(",")[-1]) == 2:
        raw = raw.replace(",", ".")
    else:
        raw = raw.replace(",", "")
    try:
        number = float(Decimal(raw))
        return -number if negative else number
    except (InvalidOperation, ValueError):
        return None

def parse_date_token(value: str | None) -> str:
    if not value:
        return ""
    token = normalize_space(value)
    for pattern in DATE_PATTERNS:
        try:
            return datetime.strptime(token, pattern).date().isoformat()
        except ValueError:
            pass
    return ""
