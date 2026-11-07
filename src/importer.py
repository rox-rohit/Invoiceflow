"""Preview-first CSV/XLSX import for ledger transactions.

No row is persisted until the caller explicitly confirms a validated preview.
"""
from __future__ import annotations

import csv
import hashlib
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
import re

from .ledger import LedgerStore, LedgerTransaction

IMPORT_TYPES = {
    "sales": "sale",
    "purchases": "purchase",
    "expenses": "expense",
    "collections": "collection",
    "supplier_payments": "supplier_payment",
    "sales_returns": "sales_return",
    "purchase_returns": "purchase_return",
}
ALIASES = {
    "transaction_date": ("date", "transaction date", "invoice date", "payment date"),
    "due_date": ("due date", "payment due", "due"),
    "amount": ("amount", "total", "value", "invoice total", "paid amount"),
    "counterparty": ("customer", "supplier", "vendor", "payee", "counterparty", "party"),
    "reference_number": ("reference", "reference number", "invoice number", "bill number", "document number"),
    "description": ("description", "details", "particulars", "memo"),
    "category": ("category", "expense category"),
    "currency": ("currency", "currency code"),
    "tax_amount": ("tax", "tax amount", "gst amount"),
    "payment_method": ("payment method", "method"),
    "payment_status": ("payment status", "status"),
}


def _key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").casefold()).strip()


def _date(value: str) -> str:
    value = str(value or "").strip()
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y", "%d %b %Y", "%d %B %Y"):
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            pass
    raise ValueError("Use an unambiguous date such as YYYY-MM-DD or DD/MM/YYYY")


def _decimal(value: str, required: bool = True) -> Decimal | None:
    text = str(value or "").strip().replace(",", "").replace("₹", "").replace("$", "").replace("€", "").replace("£", "")
    if not text:
        if required: raise ValueError("Amount is required")
        return None
    try:
        result = Decimal(text).quantize(Decimal("0.01"))
    except InvalidOperation as exc:
        raise ValueError("Amount is not a valid number") from exc
    if not result.is_finite(): raise ValueError("Amount must be finite")
    return result


@dataclass
class ImportRow:
    row_number: int
    values: dict[str, str]
    transaction: LedgerTransaction | None = None
    errors: list[str] = field(default_factory=list)
    duplicate_of: int | None = None


@dataclass
class ImportPreview:
    path: Path
    import_type: str
    file_sha256: str
    columns: list[str]
    mapping: dict[str, str]
    rows: list[ImportRow]
    already_imported: bool = False

    @property
    def valid_count(self): return sum(not r.errors and r.transaction is not None and r.duplicate_of is None for r in self.rows)
    @property
    def invalid_count(self): return sum(bool(r.errors) for r in self.rows)
    @property
    def duplicate_count(self): return sum(r.duplicate_of is not None for r in self.rows)


class ImportService:
    def __init__(self, store: LedgerStore, max_rows: int = 100_000):
        self.store, self.max_rows = store, max_rows

    def preview(self, path: str | Path, import_type: str, mapping: dict[str, str] | None = None) -> ImportPreview:
        path = Path(path)
        if import_type not in IMPORT_TYPES: raise ValueError(f"Unsupported import type: {import_type}")
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""): digest.update(chunk)
        sha = digest.hexdigest()
        if path.suffix.casefold() == ".csv":
            with path.open("r", encoding="utf-8-sig", newline="") as stream:
                reader = csv.DictReader(stream); columns = list(reader.fieldnames or []); data = list(reader)
        elif path.suffix.casefold() in {".xlsx", ".xlsm"}:
            from openpyxl import load_workbook
            workbook = load_workbook(path, read_only=True, data_only=True)
            try:
                sheet = workbook.active; iterator = sheet.iter_rows(values_only=True)
                columns = [str(x or "").strip() for x in next(iterator, ())]
                data = [dict(zip(columns, ("" if x is None else str(x) for x in row))) for row in iterator if any(x is not None for x in row)]
            finally: workbook.close()
        else: raise ValueError("Choose a CSV or Excel .xlsx file")
        if len(data) > self.max_rows: raise ValueError(f"Import exceeds the {self.max_rows:,}-row limit")
        normalized = {_key(c): c for c in columns}
        selected = dict(mapping or {})
        for field_name, aliases in ALIASES.items():
            if field_name in selected: continue
            selected[field_name] = next((normalized[_key(alias)] for alias in aliases if _key(alias) in normalized), "")
        preview = ImportPreview(path, import_type, sha, columns, selected, [])
        prior = self.store.conn.execute("SELECT import_batch_id FROM ledger_import_batches WHERE business_id=1 AND file_sha256=? AND import_type=?", (sha, import_type)).fetchone()
        preview.already_imported = prior is not None
        seen: dict[tuple, int] = {}
        for number, source in enumerate(data, 2):
            row = {str(k): "" if v is None else str(v) for k, v in source.items()}
            values = {field: row.get(column, "").strip() if column else "" for field, column in selected.items()}
            item = ImportRow(number, values)
            try:
                when = _date(values.get("transaction_date", ""))
                amount = _decimal(values.get("amount", ""))
                kind = IMPORT_TYPES[import_type]
                party = values.get("counterparty", "").strip()
                if kind in {"sale", "purchase", "collection", "supplier_payment", "sales_return", "purchase_return"} and not party:
                    raise ValueError("Customer or supplier is required")
                currency = values.get("currency", "INR").strip().upper() or "INR"
                if not re.fullmatch(r"[A-Z]{3}", currency): raise ValueError("Currency must be a three-letter code")
                due_date = _date(values.get("due_date", "")) if values.get("due_date", "").strip() else ""
                tx = LedgerTransaction(transaction_type=kind, transaction_date=when, document_date=when, due_date=due_date,
                    counterparty=party, reference_number=values.get("reference_number", "").strip(),
                    description=values.get("description", "").strip(), category=values.get("category", "").strip(),
                    amount=amount, tax_amount=_decimal(values.get("tax_amount", ""), False), currency=currency,
                    payment_method=values.get("payment_method", "").strip(), payment_status="unknown",
                    verification_status="USER_REVIEWED", source_file=path.name,
                    metadata={"import_source": path.name, "import_row": number})
                identity = (kind, when, _key(party), _key(tx.reference_number), amount, currency)
                found = self.store.conn.execute("SELECT transaction_id FROM financial_transactions WHERE business_id=1 AND transaction_type=? AND transaction_date=? AND lower(trim(counterparty))=lower(trim(?)) AND amount=? AND currency=? AND verification_status NOT IN ('REJECTED','REVERSED') LIMIT 1", (kind, when, party, str(amount), currency)).fetchone()
                if found: item.duplicate_of = int(found[0])
                elif identity in seen: item.duplicate_of = seen[identity]
                else: seen[identity] = number
                item.transaction = tx
            except (ValueError, TypeError) as exc: item.errors.append(str(exc))
            preview.rows.append(item)
        return preview

    def confirm(self, preview: ImportPreview, include_duplicates: bool = False) -> dict:
        if preview.already_imported:
            return {"batch_id": None, "imported": 0, "already_imported": True, "invalid": preview.invalid_count, "duplicates": preview.duplicate_count}
        accepted = [(r.row_number, r.transaction) for r in preview.rows if not r.errors and r.transaction and (include_duplicates or r.duplicate_of is None)]
        errors = [f"Row {row.row_number}: " + "; ".join(row.errors) for row in preview.rows if row.errors]
        batch_id, count, duplicate_file = self.store.import_batch(
            preview.path.name,
            preview.file_sha256,
            preview.import_type,
            accepted,
            rejected_rows=preview.invalid_count,
            duplicate_rows=preview.duplicate_count,
            error_details=errors,
            total_rows=len(preview.rows),
        )
        return {"batch_id": batch_id, "imported": count, "already_imported": duplicate_file, "invalid": preview.invalid_count, "duplicates": preview.duplicate_count}

    @staticmethod
    def write_template(path: str | Path, import_type: str, excel: bool = False) -> Path:
        if import_type not in IMPORT_TYPES: raise ValueError(import_type)
        columns = ["Date", "Amount", "Currency", "Customer" if import_type in {"sales", "collections", "sales_returns"} else "Supplier", "Reference", "Description", "Category", "Tax Amount", "Payment Method"]
        path = Path(path)
        if excel:
            from openpyxl import Workbook
            book = Workbook(); book.active.append(columns); book.save(path)
        else:
            with path.open("w", encoding="utf-8-sig", newline="") as stream: csv.writer(stream).writerow(columns)
        return path
