from __future__ import annotations
import re
from .models import LineItem
from .utils import normalize_space, parse_amount

def extract_line_items(page_text: str) -> list[LineItem]:
    lines = [normalize_space(x) for x in page_text.splitlines() if normalize_space(x)]
    header_index = next((i for i, line in enumerate(lines) if re.search(r"\b(description|particulars|item|product)\b", line, re.I) and (re.search(r"\b(qty|quantity|rate|unit price|amount|total)\b", line, re.I) or any(re.search(r"\b(qty|quantity|rate|unit price|amount|total|net price|gross)\b", x, re.I) for x in lines[i+1:i+8]))), -1)
    if header_index < 0:
        return []
    vertical: list[LineItem] = []
    cursor = header_index + 1
    while cursor < len(lines):
        row_index = next((i for i in range(cursor, len(lines)) if re.fullmatch(r"\d+[.)]", lines[i])), None)
        if row_index is None: break
        description_lines=[x for x in lines[cursor:row_index] if x not in {"ITEMS","Description","Qty","UM","Net price","Net worth","VAT [%]","Gross","worth"} and not re.search(r"\b(summary|total|vat)\b",x,re.I) and not re.fullmatch(r"[\d,.%$€£₹ -]+",x)]
        pointer=row_index+1; raw_values=[]; unit=""
        while pointer < len(lines):
            candidate=lines[pointer]
            if re.fullmatch(r"\d+[.)]",candidate): break
            value=parse_amount(candidate.replace("%",""))
            if value is not None: raw_values.append(value)
            elif not raw_values and candidate.lower() not in {"qty","um","net price","net worth","vat [%]","gross","worth"}: unit=candidate
            elif len(raw_values) >= 4: break
            pointer += 1
        if description_lines and len(raw_values) >= 4:
            tax_rate=raw_values[3] if len(raw_values)>=5 and raw_values[3] <= 100 else None
            line_total=raw_values[4] if len(raw_values)>=5 else raw_values[-1]
            vertical.append(LineItem(description=" ".join(description_lines), quantity=raw_values[0], unit=unit, unit_price=raw_values[1], tax_rate=tax_rate, total=line_total, source_row=row_index))
        cursor=max(pointer,cursor+1)
    if vertical:
        return vertical
    items: list[LineItem] = []
    for row, line in enumerate(lines[header_index + 1:], start=header_index + 1):
        if re.search(r"\b(subtotal|grand total|invoice total|total due|tax|gst|vat)\b", line, re.I):
            if items:
                break
            continue
        nums = re.findall(r"[-+]?\d[\d,]*(?:\.\d+)?", line)
        if not nums:
            if items and len(line) < 160:
                items[-1].description = normalize_space(items[-1].description + " " + line)
            continue
        values = [parse_amount(n) for n in nums]
        description = line
        for n in nums:
            description = re.sub(r"(?<!\w)" + re.escape(n) + r"(?!\w)", "", description, count=1)
        description = normalize_space(description).strip("|-:")
        if not description:
            continue
        items.append(LineItem(description=description, quantity=values[0], unit="", unit_price=values[-2] if len(values) >= 2 else None, total=values[-1], source_row=row))
    return items
