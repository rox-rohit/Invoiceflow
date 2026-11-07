from __future__ import annotations
import json, sqlite3
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
from .models import InvoiceRecord

TRANSACTION_TYPES={"sale","sales_return","purchase","purchase_return","expense","collection","supplier_payment","payroll","employee_advance","reimbursement","loan_receipt","loan_repayment","owner_capital","owner_withdrawal","tax_payment","bank_charge","adjustment"}
PAYMENT_STATUSES={"unpaid","partially_paid","paid","not_applicable","unknown"}
VERIFICATION_STATUSES={"PROPOSED","VERIFIED","REJECTED","DRAFT"}

def money(value: Decimal | float | int | str | None) -> Decimal | None:
    if value is None or value=="": return None
    try: return Decimal(str(value)).quantize(Decimal("0.01"))
    except InvalidOperation as exc: raise ValueError(f"Invalid monetary value: {value}") from exc

@dataclass
class LedgerTransaction:
    transaction_id: int | None = None
    business_id: int = 1
    transaction_type: str = "adjustment"
    transaction_date: str = ""
    document_date: str = ""
    due_date: str = ""
    counterparty: str = ""
    reference_number: str = ""
    description: str = ""
    category: str = ""
    subcategory: str = ""
    amount: Decimal | None = None
    tax_amount: Decimal | None = None
    currency: str = ""
    payment_status: str = "unknown"
    payment_method: str = ""
    source_record_id: int | None = None
    source_file: str = ""
    verification_status: str = "DRAFT"
    created_at: str = ""
    updated_at: str = ""
    metadata: dict[str,Any] = field(default_factory=dict)

    def __post_init__(self):
        self.amount=money(self.amount); self.tax_amount=money(self.tax_amount)
        if self.transaction_type not in TRANSACTION_TYPES: raise ValueError(f"Unsupported transaction type: {self.transaction_type}")
        if self.payment_status not in PAYMENT_STATUSES: raise ValueError(f"Unsupported payment status: {self.payment_status}")
        if self.verification_status not in VERIFICATION_STATUSES: raise ValueError(f"Unsupported verification status: {self.verification_status}")

    def to_dict(self):
        data=asdict(self); data["amount"]=None if self.amount is None else str(self.amount); data["tax_amount"]=None if self.tax_amount is None else str(self.tax_amount); return data

    @classmethod
    def from_row(cls,row):
        data=dict(row); data["metadata"]=json.loads(data.pop("metadata_json") or "{}"); return cls(**data)

class LedgerStore:
    def __init__(self,path: str | Path):
        self.path=Path(path); self.path.parent.mkdir(parents=True,exist_ok=True); self.conn=sqlite3.connect(self.path); self.conn.row_factory=sqlite3.Row; self.conn.execute("PRAGMA foreign_keys=ON"); self.migrate()

    def migrate(self):
        self.conn.execute("CREATE TABLE IF NOT EXISTS schema_migrations (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)")
        self.conn.execute("CREATE TABLE IF NOT EXISTS businesses (business_id INTEGER PRIMARY KEY, name TEXT NOT NULL, base_currency TEXT NOT NULL DEFAULT 'INR', created_at TEXT NOT NULL)")
        self.conn.execute("CREATE TABLE IF NOT EXISTS financial_transactions (transaction_id INTEGER PRIMARY KEY, business_id INTEGER NOT NULL, transaction_type TEXT NOT NULL, transaction_date TEXT NOT NULL, document_date TEXT, due_date TEXT, counterparty TEXT, reference_number TEXT, description TEXT, category TEXT, subcategory TEXT, amount TEXT, tax_amount TEXT, currency TEXT, payment_status TEXT NOT NULL, payment_method TEXT, source_record_id INTEGER, source_file TEXT, verification_status TEXT NOT NULL, metadata_json TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL, updated_at TEXT NOT NULL, FOREIGN KEY(business_id) REFERENCES businesses(business_id))")
        self.conn.execute("CREATE TABLE IF NOT EXISTS transaction_audit (audit_id INTEGER PRIMARY KEY, transaction_id INTEGER NOT NULL, action TEXT NOT NULL, before_json TEXT, after_json TEXT, changed_at TEXT NOT NULL, FOREIGN KEY(transaction_id) REFERENCES financial_transactions(transaction_id))")
        self.conn.execute("CREATE TABLE IF NOT EXISTS budgets (budget_id INTEGER PRIMARY KEY, business_id INTEGER NOT NULL, period_start TEXT NOT NULL, period_end TEXT NOT NULL, category TEXT NOT NULL, amount TEXT NOT NULL, currency TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL, FOREIGN KEY(business_id) REFERENCES businesses(business_id))")
        budget_columns={row[1] for row in self.conn.execute("PRAGMA table_info(budgets)").fetchall()}
        if "active" not in budget_columns: self.conn.execute("ALTER TABLE budgets ADD COLUMN active INTEGER NOT NULL DEFAULT 1")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_financial_transactions_date ON financial_transactions(business_id,transaction_date)"); self.conn.execute("CREATE INDEX IF NOT EXISTS idx_financial_transactions_type ON financial_transactions(business_id,transaction_type)"); self.conn.execute("CREATE INDEX IF NOT EXISTS idx_financial_transactions_source ON financial_transactions(source_record_id)")
        self.conn.execute("INSERT OR IGNORE INTO businesses(business_id,name,base_currency,created_at) VALUES(1,'Default business','INR',?)",(datetime.now(timezone.utc).isoformat(),)); self.conn.execute("INSERT OR IGNORE INTO schema_migrations(version,applied_at) VALUES(1,?)",(datetime.now(timezone.utc).isoformat(),)); self.conn.commit()

    def add(self,transaction: LedgerTransaction) -> LedgerTransaction:
        now=datetime.now(timezone.utc).isoformat(); transaction.created_at=transaction.created_at or now; transaction.updated_at=now
        cursor=self.conn.execute("INSERT INTO financial_transactions(business_id,transaction_type,transaction_date,document_date,due_date,counterparty,reference_number,description,category,subcategory,amount,tax_amount,currency,payment_status,payment_method,source_record_id,source_file,verification_status,metadata_json,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(transaction.business_id,transaction.transaction_type,transaction.transaction_date,transaction.document_date,transaction.due_date,transaction.counterparty,transaction.reference_number,transaction.description,transaction.category,transaction.subcategory,str(transaction.amount) if transaction.amount is not None else None,str(transaction.tax_amount) if transaction.tax_amount is not None else None,transaction.currency,transaction.payment_status,transaction.payment_method,transaction.source_record_id,transaction.source_file,transaction.verification_status,json.dumps(transaction.metadata),transaction.created_at,transaction.updated_at)); transaction.transaction_id=cursor.lastrowid; self.conn.execute("INSERT INTO transaction_audit(transaction_id,action,after_json,changed_at) VALUES(?,?,?,?)",(transaction.transaction_id,"CREATE",json.dumps(transaction.to_dict(),default=str),now)); self.conn.commit(); return transaction

    def propose_from_invoice(self,record: InvoiceRecord, transaction_type: str) -> LedgerTransaction:
        if transaction_type not in {"sale","purchase","sales_return","purchase_return","expense"}: raise ValueError("A user or import must explicitly choose the proposed transaction type")
        return LedgerTransaction(transaction_type=transaction_type,transaction_date=record.invoice_date,document_date=record.invoice_date,due_date=record.due_date,counterparty=record.vendor_name if transaction_type in {"purchase","purchase_return","expense"} else record.customer_name,reference_number=record.invoice_number,description=f"Proposed from {record.document_type}",amount=record.total_amount,tax_amount=record.tax_amount,currency=record.currency,source_record_id=record.record_id,source_file=record.source_file,verification_status="PROPOSED",metadata={"source_sha256":record.source_sha256,"extraction_version":record.extraction_version})

    def verify(self,transaction_id: int, status: str="VERIFIED") -> None:
        if status not in {"VERIFIED","REJECTED"}: raise ValueError(status)
        row=self.conn.execute("SELECT * FROM financial_transactions WHERE transaction_id=?",(transaction_id,)).fetchone()
        if not row: raise KeyError(transaction_id)
        before=dict(row); now=datetime.now(timezone.utc).isoformat(); self.conn.execute("UPDATE financial_transactions SET verification_status=?,updated_at=? WHERE transaction_id=?",(status,now,transaction_id)); after=dict(self.conn.execute("SELECT * FROM financial_transactions WHERE transaction_id=?",(transaction_id,)).fetchone()); self.conn.execute("INSERT INTO transaction_audit(transaction_id,action,before_json,after_json,changed_at) VALUES(?,?,?,?,?)",(transaction_id,"VERIFY",json.dumps(before,default=str),json.dumps(after,default=str),now)); self.conn.commit()

    def list(self,business_id: int=1, start: str | None=None, end: str | None=None, verified_only: bool=False) -> list[LedgerTransaction]:
        sql="SELECT * FROM financial_transactions WHERE business_id=?"; args=[business_id]
        if start: sql+=" AND transaction_date>=?"; args.append(start)
        if end: sql+=" AND transaction_date<=?"; args.append(end)
        if verified_only: sql+=" AND verification_status='VERIFIED'"
        sql+=" ORDER BY transaction_date,transaction_id"; return [LedgerTransaction.from_row(row) for row in self.conn.execute(sql,args).fetchall()]

    def add_budget(self,business_id: int, start: str, end: str, category: str, amount: Decimal | float | str, currency: str) -> int:
        now=datetime.now(timezone.utc).isoformat(); cursor=self.conn.execute("INSERT INTO budgets(business_id,period_start,period_end,category,amount,currency,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)",(business_id,start,end,category,str(money(amount)),currency,now,now)); self.conn.commit(); return int(cursor.lastrowid)

    def list_budgets(self, business_id: int = 1, active_only: bool = False) -> list[dict]:
        sql="SELECT * FROM budgets WHERE business_id=?"; args=[business_id]
        if active_only: sql += " AND active=1"
        sql += " ORDER BY period_start, category, budget_id"
        return [dict(row) for row in self.conn.execute(sql, args).fetchall()]

    def update_budget(self, budget_id: int, start: str, end: str, category: str, amount: Decimal | float | str, currency: str) -> None:
        now=datetime.now(timezone.utc).isoformat(); self.conn.execute("UPDATE budgets SET period_start=?,period_end=?,category=?,amount=?,currency=?,updated_at=? WHERE budget_id=?",(start,end,category,str(money(amount)),currency,now,budget_id)); self.conn.commit()

    def set_budget_active(self, budget_id: int, active: bool) -> None:
        now=datetime.now(timezone.utc).isoformat(); self.conn.execute("UPDATE budgets SET active=?,updated_at=? WHERE budget_id=?",(int(active),now,budget_id)); self.conn.commit()

    def backup_to(self,destination: str | Path) -> Path:
        destination=Path(destination); destination.parent.mkdir(parents=True,exist_ok=True); self.conn.commit()
        with sqlite3.connect(destination) as target: self.conn.backup(target)
        return destination

    def close(self): self.conn.close()
