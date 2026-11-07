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
VERIFICATION_STATUSES={"PROPOSED","USER_REVIEWED","VERIFIED","REJECTED","DRAFT","REVERSED"}

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
        data=dict(row); data.pop("import_batch_id",None); data.pop("import_row_number",None); data["metadata"]=json.loads(data.pop("metadata_json") or "{}"); return cls(**data)

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
        self.conn.execute("INSERT OR IGNORE INTO businesses(business_id,name,base_currency,created_at) VALUES(1,'Default business','INR',?)",(datetime.now(timezone.utc).isoformat(),)); self.conn.execute("INSERT OR IGNORE INTO schema_migrations(version,applied_at) VALUES(1,?)",(datetime.now(timezone.utc).isoformat(),))
        # Additive 2.4 migration: provenance and explicit payment allocations.
        columns={row[1] for row in self.conn.execute("PRAGMA table_info(financial_transactions)")}
        if "import_batch_id" not in columns: self.conn.execute("ALTER TABLE financial_transactions ADD COLUMN import_batch_id INTEGER REFERENCES ledger_import_batches(import_batch_id)")
        if "import_row_number" not in columns: self.conn.execute("ALTER TABLE financial_transactions ADD COLUMN import_row_number INTEGER")
        self.conn.execute("CREATE TABLE IF NOT EXISTS ledger_import_batches(import_batch_id INTEGER PRIMARY KEY,business_id INTEGER NOT NULL,file_name TEXT NOT NULL,file_sha256 TEXT NOT NULL,import_type TEXT NOT NULL,status TEXT NOT NULL,created_at TEXT NOT NULL,record_count INTEGER NOT NULL DEFAULT 0,UNIQUE(business_id,file_sha256,import_type),FOREIGN KEY(business_id) REFERENCES businesses(business_id))")
        self.conn.execute("CREATE TABLE IF NOT EXISTS payment_allocations(allocation_id INTEGER PRIMARY KEY,business_id INTEGER NOT NULL,payment_transaction_id INTEGER NOT NULL,invoice_transaction_id INTEGER NOT NULL,amount TEXT NOT NULL,currency TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'ACTIVE',created_at TEXT NOT NULL,FOREIGN KEY(payment_transaction_id) REFERENCES financial_transactions(transaction_id),FOREIGN KEY(invoice_transaction_id) REFERENCES financial_transactions(transaction_id),CHECK(payment_transaction_id<>invoice_transaction_id))")
        self.conn.execute("CREATE TABLE IF NOT EXISTS allocation_audit(audit_id INTEGER PRIMARY KEY,allocation_id INTEGER NOT NULL,action TEXT NOT NULL,before_json TEXT,after_json TEXT,changed_at TEXT NOT NULL,FOREIGN KEY(allocation_id) REFERENCES payment_allocations(allocation_id))")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_alloc_invoice ON payment_allocations(invoice_transaction_id,status)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_alloc_payment ON payment_allocations(payment_transaction_id,status)")
        self.conn.execute("INSERT OR IGNORE INTO schema_migrations(version,applied_at) VALUES(2,?)",(datetime.now(timezone.utc).isoformat(),)); self.conn.commit()
        batch_columns={row[1] for row in self.conn.execute("PRAGMA table_info(ledger_import_batches)")}
        for name, definition in (("total_rows", "INTEGER NOT NULL DEFAULT 0"), ("successful_rows", "INTEGER NOT NULL DEFAULT 0"), ("rejected_rows", "INTEGER NOT NULL DEFAULT 0"), ("duplicate_rows", "INTEGER NOT NULL DEFAULT 0"), ("error_details_json", "TEXT NOT NULL DEFAULT '[]'")):
            if name not in batch_columns: self.conn.execute(f"ALTER TABLE ledger_import_batches ADD COLUMN {name} {definition}")
        self.conn.execute("CREATE TABLE IF NOT EXISTS contacts(contact_id INTEGER PRIMARY KEY,business_id INTEGER NOT NULL,name TEXT NOT NULL,phone TEXT,email TEXT,address TEXT,gstin TEXT,role TEXT NOT NULL,opening_balance TEXT NOT NULL DEFAULT '0.00',payment_terms TEXT,notes TEXT,active INTEGER NOT NULL DEFAULT 1,created_at TEXT NOT NULL,updated_at TEXT NOT NULL,UNIQUE(business_id,name,role),FOREIGN KEY(business_id) REFERENCES businesses(business_id))")
        self.conn.execute("CREATE TABLE IF NOT EXISTS app_settings(setting_key TEXT PRIMARY KEY,setting_value TEXT NOT NULL,updated_at TEXT NOT NULL)")
        self.conn.execute("CREATE TABLE IF NOT EXISTS backup_history(backup_id INTEGER PRIMARY KEY,path TEXT NOT NULL,created_at TEXT NOT NULL,size_bytes INTEGER NOT NULL,integrity_ok INTEGER NOT NULL)")
        self.conn.execute("INSERT OR IGNORE INTO schema_migrations(version,applied_at) VALUES(3,?)",(datetime.now(timezone.utc).isoformat(),)); self.conn.commit()

    def add(self,transaction: LedgerTransaction) -> LedgerTransaction:
        now=datetime.now(timezone.utc).isoformat(); transaction.created_at=transaction.created_at or now; transaction.updated_at=now
        cursor=self.conn.execute("INSERT INTO financial_transactions(business_id,transaction_type,transaction_date,document_date,due_date,counterparty,reference_number,description,category,subcategory,amount,tax_amount,currency,payment_status,payment_method,source_record_id,source_file,verification_status,metadata_json,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(transaction.business_id,transaction.transaction_type,transaction.transaction_date,transaction.document_date,transaction.due_date,transaction.counterparty,transaction.reference_number,transaction.description,transaction.category,transaction.subcategory,str(transaction.amount) if transaction.amount is not None else None,str(transaction.tax_amount) if transaction.tax_amount is not None else None,transaction.currency,transaction.payment_status,transaction.payment_method,transaction.source_record_id,transaction.source_file,transaction.verification_status,json.dumps(transaction.metadata),transaction.created_at,transaction.updated_at)); transaction.transaction_id=cursor.lastrowid; self.conn.execute("INSERT INTO transaction_audit(transaction_id,action,after_json,changed_at) VALUES(?,?,?,?)",(transaction.transaction_id,"CREATE",json.dumps(transaction.to_dict(),default=str),now)); self.conn.commit(); return transaction

    def import_batch(self, file_name: str, file_sha256: str, import_type: str, rows: list[tuple[int, LedgerTransaction]], rejected_rows: int = 0, duplicate_rows: int = 0, error_details: list[str] | None = None, total_rows: int | None = None) -> tuple[int, int, bool]:
        """Atomically persist a confirmed import; re-importing identical source is idempotent."""
        now=datetime.now(timezone.utc).isoformat()
        try:
            with self.conn:
                total_rows = len(rows) + rejected_rows if total_rows is None else total_rows
                cursor=self.conn.execute("INSERT INTO ledger_import_batches(business_id,file_name,file_sha256,import_type,status,created_at,record_count,total_rows,successful_rows,rejected_rows,duplicate_rows,error_details_json) VALUES(1,?,?,?,'COMPLETED',?,?,?,?,?,?,?)",(file_name,file_sha256,import_type,now,len(rows),total_rows,len(rows),rejected_rows,duplicate_rows,json.dumps(error_details or [])))
                batch_id=int(cursor.lastrowid)
                for row_number,tx in rows:
                    tx.created_at=tx.created_at or now; tx.updated_at=now
                    cur=self.conn.execute("INSERT INTO financial_transactions(business_id,transaction_type,transaction_date,document_date,due_date,counterparty,reference_number,description,category,subcategory,amount,tax_amount,currency,payment_status,payment_method,source_record_id,source_file,verification_status,metadata_json,created_at,updated_at,import_batch_id,import_row_number) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(tx.business_id,tx.transaction_type,tx.transaction_date,tx.document_date,tx.due_date,tx.counterparty,tx.reference_number,tx.description,tx.category,tx.subcategory,str(tx.amount) if tx.amount is not None else None,str(tx.tax_amount) if tx.tax_amount is not None else None,tx.currency,tx.payment_status,tx.payment_method,tx.source_record_id,tx.source_file or file_name,tx.verification_status,json.dumps(tx.metadata),now,now,batch_id,row_number))
                    tx.transaction_id=int(cur.lastrowid)
                    self.conn.execute("INSERT INTO transaction_audit(transaction_id,action,after_json,changed_at) VALUES(?,?,?,?)",(tx.transaction_id,"IMPORT",json.dumps(tx.to_dict(),default=str),now))
            return batch_id,len(rows),False
        except sqlite3.IntegrityError as exc:
            if "UNIQUE constraint failed: ledger_import_batches" not in str(exc): raise
            existing=self.conn.execute("SELECT import_batch_id,record_count FROM ledger_import_batches WHERE business_id=1 AND file_sha256=? AND import_type=?",(file_sha256,import_type)).fetchone()
            return int(existing[0]),0,True

    def allocate_payment(self, payment_transaction_id: int, invoice_transaction_id: int, amount: Decimal | str | int) -> int:
        value=money(amount)
        if value is None or value<=0: raise ValueError("Allocation amount must be greater than zero")
        payment=self.conn.execute("SELECT * FROM financial_transactions WHERE transaction_id=?",(payment_transaction_id,)).fetchone()
        invoice=self.conn.execute("SELECT * FROM financial_transactions WHERE transaction_id=?",(invoice_transaction_id,)).fetchone()
        if not payment or not invoice: raise KeyError("Payment or invoice transaction was not found")
        ptype,itype=payment["transaction_type"],invoice["transaction_type"]
        if (ptype,itype) not in (("collection","sale"),("supplier_payment","purchase"),("payment","purchase")):
            raise ValueError("Payment and invoice transaction types are not compatible")
        if payment["business_id"]!=invoice["business_id"] or (payment["counterparty"] or "").strip().casefold()!=(invoice["counterparty"] or "").strip().casefold(): raise ValueError("Payment and invoice must belong to the same business and counterparty")
        if payment["currency"]!=invoice["currency"]: raise ValueError("Payment and invoice currencies must match")
        if payment["verification_status"] not in {"VERIFIED","USER_REVIEWED"} or invoice["verification_status"] not in {"VERIFIED","USER_REVIEWED"}: raise ValueError("Both records must be reviewed before allocation")
        used=sum((Decimal(r[0]) for r in self.conn.execute("SELECT amount FROM payment_allocations WHERE payment_transaction_id=? AND status='ACTIVE'",(payment_transaction_id,))),Decimal("0.00"))
        invoice_used=sum((Decimal(r[0]) for r in self.conn.execute("SELECT amount FROM payment_allocations WHERE invoice_transaction_id=? AND status='ACTIVE'",(invoice_transaction_id,))),Decimal("0.00"))
        if used+value>Decimal(payment["amount"]): raise ValueError("Allocation exceeds the unallocated payment amount")
        if invoice_used+value>Decimal(invoice["amount"]): raise ValueError("Allocation exceeds the invoice outstanding balance")
        now=datetime.now(timezone.utc).isoformat()
        with self.conn:
            cur=self.conn.execute("INSERT INTO payment_allocations(business_id,payment_transaction_id,invoice_transaction_id,amount,currency,created_at) VALUES(?,?,?,?,?,?)",(payment["business_id"],payment_transaction_id,invoice_transaction_id,str(value),payment["currency"],now))
            allocation_id=int(cur.lastrowid); after={"allocation_id":allocation_id,"payment_transaction_id":payment_transaction_id,"invoice_transaction_id":invoice_transaction_id,"amount":str(value),"currency":payment["currency"],"status":"ACTIVE"}
            self.conn.execute("INSERT INTO allocation_audit(allocation_id,action,after_json,changed_at) VALUES(?,?,?,?)",(allocation_id,"CREATE",json.dumps(after),now))
        return allocation_id

    def reverse_allocation(self, allocation_id: int, reason: str) -> None:
        if not reason.strip(): raise ValueError("A reason is required to reverse an allocation")
        row=self.conn.execute("SELECT * FROM payment_allocations WHERE allocation_id=?",(allocation_id,)).fetchone()
        if not row: raise KeyError(allocation_id)
        if row["status"]!="ACTIVE": raise ValueError("Only active allocations can be reversed")
        before=dict(row); now=datetime.now(timezone.utc).isoformat()
        with self.conn:
            self.conn.execute("UPDATE payment_allocations SET status='REVERSED' WHERE allocation_id=?",(allocation_id,))
            after=dict(self.conn.execute("SELECT * FROM payment_allocations WHERE allocation_id=?",(allocation_id,)).fetchone()); after["reason"]=reason
            self.conn.execute("INSERT INTO allocation_audit(allocation_id,action,before_json,after_json,changed_at) VALUES(?,?,?,?,?)",(allocation_id,"REVERSE",json.dumps(before,default=str),json.dumps(after,default=str),now))

    def allocation_summary(self, transaction_id: int) -> dict[str, Decimal | str]:
        row=self.conn.execute("SELECT * FROM financial_transactions WHERE transaction_id=?",(transaction_id,)).fetchone()
        if not row: raise KeyError(transaction_id)
        allocated=sum((Decimal(r[0]) for r in self.conn.execute("SELECT amount FROM payment_allocations WHERE invoice_transaction_id=? AND status='ACTIVE'",(transaction_id,))),Decimal("0.00"))
        if row["transaction_type"] in {"collection","supplier_payment","payment"}:
            allocated=sum((Decimal(r[0]) for r in self.conn.execute("SELECT amount FROM payment_allocations WHERE payment_transaction_id=? AND status='ACTIVE'",(transaction_id,))),Decimal("0.00"))
            remaining=Decimal(row["amount"] or "0")-allocated
            return {"allocated":allocated,"remaining":remaining,"status":"allocated" if remaining==0 else "partially_allocated" if allocated else "unallocated"}
        total=Decimal(row["amount"] or "0"); remaining=total-allocated
        return {"allocated":allocated,"remaining":remaining,"status":"paid" if remaining==0 else "partially_paid" if allocated else "unpaid"}

    def list_allocations(self, transaction_id: int | None=None) -> list[dict]:
        sql="SELECT a.*,p.counterparty,p.transaction_date AS payment_date,i.reference_number AS invoice_reference,i.transaction_date AS invoice_date FROM payment_allocations a JOIN financial_transactions p ON p.transaction_id=a.payment_transaction_id JOIN financial_transactions i ON i.transaction_id=a.invoice_transaction_id"
        args=()
        if transaction_id is not None: sql+=" WHERE a.payment_transaction_id=? OR a.invoice_transaction_id=?"; args=(transaction_id,transaction_id)
        return [dict(row) for row in self.conn.execute(sql+" ORDER BY a.allocation_id",args).fetchall()]

    def list_import_batches(self, business_id: int = 1) -> list[dict]:
        """Return the immutable import audit trail newest first."""
        rows = self.conn.execute(
            "SELECT import_batch_id, file_name, file_sha256, import_type, status, "
            "created_at, record_count, total_rows, successful_rows, rejected_rows, duplicate_rows, error_details_json FROM ledger_import_batches "
            "WHERE business_id=? ORDER BY created_at DESC, import_batch_id DESC",
            (business_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    def get_setting(self, key: str, default: str = "") -> str:
        row = self.conn.execute("SELECT setting_value FROM app_settings WHERE setting_key=?", (key,)).fetchone()
        return str(row[0]) if row else default

    def set_setting(self, key: str, value: str) -> None:
        now=datetime.now(timezone.utc).isoformat()
        self.conn.execute("INSERT INTO app_settings(setting_key,setting_value,updated_at) VALUES(?,?,?) ON CONFLICT(setting_key) DO UPDATE SET setting_value=excluded.setting_value,updated_at=excluded.updated_at",(key,str(value),now))
        self.conn.commit()

    def get_business_profile(self) -> dict:
        row=self.conn.execute("SELECT * FROM businesses WHERE business_id=1").fetchone()
        return dict(row) if row else {}

    def update_business_profile(self, **values) -> None:
        allowed={"name","owner_name","business_type","address","phone","email","gstin","base_currency","financial_year_start","payment_terms","logo_path"}
        values={key:value for key,value in values.items() if key in allowed}
        columns={row[1] for row in self.conn.execute("PRAGMA table_info(businesses)")}
        for key in ("owner_name","business_type","address","phone","email","gstin","financial_year_start","payment_terms","logo_path"):
            if key not in columns: self.conn.execute(f"ALTER TABLE businesses ADD COLUMN {key} TEXT")
        if values:
            values["business_id"]=1
            assignments=", ".join(f"{key}=?" for key in values if key!="business_id")
            self.conn.execute(f"UPDATE businesses SET {assignments} WHERE business_id=1", tuple(value for key,value in values.items() if key!="business_id"))
            self.conn.commit()

    def list_contacts(self, role: str | None = None, active_only: bool = False) -> list[dict]:
        sql="SELECT * FROM contacts WHERE business_id=1"; args=[]
        if role: sql+=" AND role=?"; args.append(role)
        if active_only: sql+=" AND active=1"
        return [dict(row) for row in self.conn.execute(sql+" ORDER BY name COLLATE NOCASE",args).fetchall()]

    def save_contact(self, contact: dict) -> int:
        now=datetime.now(timezone.utc).isoformat()
        fields=("name","phone","email","address","gstin","role","opening_balance","payment_terms","notes","active")
        name=str(contact.get("name","")).strip()
        role=str(contact.get("role","customer")).strip().lower()
        if not name or role not in {"customer","supplier"}: raise ValueError("A valid name and contact role are required")
        values=[name,contact.get("phone",""),contact.get("email",""),contact.get("address",""),contact.get("gstin",""),role,str(money(contact.get("opening_balance") or "0.00")),contact.get("payment_terms",""),contact.get("notes",""),int(contact.get("active",1))]
        if contact.get("contact_id"):
            self.conn.execute("UPDATE contacts SET "+", ".join(f"{field}=?" for field in fields)+",updated_at=? WHERE contact_id=? AND business_id=1",(*values,now,int(contact["contact_id"])))
            contact_id=int(contact["contact_id"])
        else:
            cur=self.conn.execute("INSERT INTO contacts(business_id,"+",".join(fields)+",created_at,updated_at) VALUES(1,"+("?,"*len(fields))+"?,?)",(*values,now,now)); contact_id=int(cur.lastrowid)
        self.conn.commit(); return contact_id

    def set_contact_active(self, contact_id: int, active: bool) -> None:
        self.conn.execute("UPDATE contacts SET active=?,updated_at=? WHERE contact_id=?",(int(active),datetime.now(timezone.utc).isoformat(),contact_id)); self.conn.commit()

    def record_backup(self, path: str | Path, integrity_ok: bool) -> None:
        target=Path(path)
        self.conn.execute("INSERT INTO backup_history(path,created_at,size_bytes,integrity_ok) VALUES(?,?,?,?)",(str(target),datetime.now(timezone.utc).isoformat(),target.stat().st_size,int(integrity_ok)))
        self.conn.commit()

    def list_backups(self) -> list[dict]:
        return [dict(row) for row in self.conn.execute("SELECT * FROM backup_history ORDER BY created_at DESC").fetchall()]

    def propose_from_invoice(self,record: InvoiceRecord, transaction_type: str) -> LedgerTransaction:
        if transaction_type not in {"sale","purchase","sales_return","purchase_return","expense"}: raise ValueError("A user or import must explicitly choose the proposed transaction type")
        return LedgerTransaction(transaction_type=transaction_type,transaction_date=record.invoice_date,document_date=record.invoice_date,due_date=record.due_date,counterparty=record.vendor_name if transaction_type in {"purchase","purchase_return","expense"} else record.customer_name,reference_number=record.invoice_number,description=f"Proposed from {record.document_type}",amount=record.total_amount,tax_amount=record.tax_amount,currency=record.currency,source_record_id=record.record_id,source_file=record.source_file,verification_status="PROPOSED",metadata={"source_sha256":record.source_sha256,"extraction_version":record.extraction_version})

    def verify(self,transaction_id: int, status: str="VERIFIED") -> None:
        if status not in {"USER_REVIEWED","VERIFIED","REJECTED"}: raise ValueError(status)
        row=self.conn.execute("SELECT * FROM financial_transactions WHERE transaction_id=?",(transaction_id,)).fetchone()
        if not row: raise KeyError(transaction_id)
        before=dict(row); now=datetime.now(timezone.utc).isoformat(); self.conn.execute("UPDATE financial_transactions SET verification_status=?,updated_at=? WHERE transaction_id=?",(status,now,transaction_id)); after=dict(self.conn.execute("SELECT * FROM financial_transactions WHERE transaction_id=?",(transaction_id,)).fetchone()); self.conn.execute("INSERT INTO transaction_audit(transaction_id,action,before_json,after_json,changed_at) VALUES(?,?,?,?,?)",(transaction_id,"VERIFY",json.dumps(before,default=str),json.dumps(after,default=str),now)); self.conn.commit()

    def list(self,business_id: int=1, start: str | None=None, end: str | None=None, verified_only: bool=False) -> list[LedgerTransaction]:
        sql="SELECT * FROM financial_transactions WHERE business_id=?"; args=[business_id]
        if start: sql+=" AND transaction_date>=?"; args.append(start)
        if end: sql+=" AND transaction_date<=?"; args.append(end)
        if verified_only: sql+=" AND verification_status IN ('VERIFIED','USER_REVIEWED')"
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

    def update_transaction(self, transaction: LedgerTransaction) -> None:
        if transaction.transaction_id is None: raise ValueError("Transaction ID is required for an update")
        existing=self.conn.execute("SELECT * FROM financial_transactions WHERE transaction_id=?",(transaction.transaction_id,)).fetchone()
        if not existing: raise KeyError(transaction.transaction_id)
        now=datetime.now(timezone.utc).isoformat(); before=dict(existing); transaction.updated_at=now
        self.conn.execute("UPDATE financial_transactions SET transaction_type=?,transaction_date=?,due_date=?,counterparty=?,reference_number=?,description=?,category=?,subcategory=?,amount=?,tax_amount=?,currency=?,payment_status=?,payment_method=?,verification_status=?,metadata_json=?,updated_at=? WHERE transaction_id=?",(transaction.transaction_type,transaction.transaction_date,transaction.due_date,transaction.counterparty,transaction.reference_number,transaction.description,transaction.category,transaction.subcategory,str(transaction.amount) if transaction.amount is not None else None,str(transaction.tax_amount) if transaction.tax_amount is not None else None,transaction.currency,transaction.payment_status,transaction.payment_method,transaction.verification_status,json.dumps(transaction.metadata),now,transaction.transaction_id))
        self.conn.execute("INSERT INTO transaction_audit(transaction_id,action,before_json,after_json,changed_at) VALUES(?,?,?,?,?)",(transaction.transaction_id,"UPDATE",json.dumps(before,default=str),json.dumps(transaction.to_dict(),default=str),now)); self.conn.commit()

    def reverse(self, transaction_id: int, reason: str) -> LedgerTransaction:
        row=self.conn.execute("SELECT * FROM financial_transactions WHERE transaction_id=?",(transaction_id,)).fetchone()
        if not row: raise KeyError(transaction_id)
        if not reason.strip(): raise ValueError("A reason is required to reverse a transaction")
        allocation_count=self.conn.execute("SELECT COUNT(*) FROM payment_allocations WHERE status='ACTIVE' AND (payment_transaction_id=? OR invoice_transaction_id=?)",(transaction_id,transaction_id)).fetchone()[0]
        if allocation_count: raise ValueError("Reverse active payment allocations before reversing this transaction")
        original=LedgerTransaction.from_row(row); reversal=LedgerTransaction(business_id=original.business_id,transaction_type="adjustment",transaction_date=original.transaction_date,document_date=original.document_date,counterparty=original.counterparty,reference_number=original.reference_number,description=f"Reversal of transaction {transaction_id}: {reason}",category=original.category,amount=-original.amount if original.amount is not None else None,tax_amount=-original.tax_amount if original.tax_amount is not None else None,currency=original.currency,payment_status="not_applicable",source_record_id=original.source_record_id,source_file=original.source_file,verification_status="VERIFIED",metadata={"reverses_transaction_id":transaction_id,"reason":reason})
        # Use the corresponding return type for invoices so existing report semantics
        # offset the original; for other transaction classes use an exact negative entry.
        reciprocal={"sale":"sales_return","sales_return":"sale","purchase":"purchase_return","purchase_return":"purchase"}
        if original.transaction_type in reciprocal:
            reversal.transaction_type=reciprocal[original.transaction_type]
            reversal.amount=abs(original.amount) if original.amount is not None else None
            reversal.tax_amount=abs(original.tax_amount) if original.tax_amount is not None else None
        else:
            reversal.transaction_type=original.transaction_type
        return self.add(reversal)

    def backup_to(self,destination: str | Path) -> Path:
        destination=Path(destination); destination.parent.mkdir(parents=True,exist_ok=True); self.conn.commit()
        with sqlite3.connect(destination) as target: self.conn.backup(target)
        return destination

    def close(self): self.conn.close()
