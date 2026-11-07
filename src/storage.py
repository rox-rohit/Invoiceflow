from __future__ import annotations
import json, shutil, sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from .models import InvoiceRecord

def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)

class HistoryStore:
    """SQLite persistence with original extraction and correction audit history."""
    def __init__(self, path: str | Path):
        self.path=Path(path); self.path.parent.mkdir(parents=True, exist_ok=True); self.conn=sqlite3.connect(self.path); self.conn.row_factory=sqlite3.Row; self._migrate()

    def _migrate(self) -> None:
        existing=self.conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='records'").fetchone()
        if existing:
            columns={row[1] for row in self.conn.execute("PRAGMA table_info(records)").fetchall()}
            if "current_payload" not in columns:
                self.conn.execute("ALTER TABLE records RENAME TO records_legacy")
        self.conn.execute("""CREATE TABLE IF NOT EXISTS records (id INTEGER PRIMARY KEY, source_file TEXT NOT NULL, source_sha256 TEXT DEFAULT '', invoice_number TEXT, status TEXT, original_payload TEXT NOT NULL, current_payload TEXT NOT NULL, created_at TEXT DEFAULT CURRENT_TIMESTAMP, updated_at TEXT DEFAULT CURRENT_TIMESTAMP)""")
        self.conn.execute("""CREATE TABLE IF NOT EXISTS correction_history (id INTEGER PRIMARY KEY, record_id INTEGER NOT NULL, field_name TEXT NOT NULL, original_value TEXT, corrected_value TEXT, corrected_at TEXT NOT NULL, FOREIGN KEY(record_id) REFERENCES records(id) ON DELETE CASCADE)""")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_records_source_hash ON records(source_sha256)"); self.conn.commit()
        if self.conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='records_legacy'").fetchone():
            rows=self.conn.execute("SELECT source_file,invoice_number,status,payload,created_at FROM records_legacy").fetchall()
            for row in rows:
                payload=row[3] or "{}"
                self.conn.execute("INSERT INTO records(source_file,invoice_number,status,original_payload,current_payload,created_at) VALUES(?,?,?,?,?,?)",(row[0],row[1],row[2],payload,payload,row[4]))
            self.conn.execute("DROP TABLE records_legacy"); self.conn.commit()

    def save(self, records: list[InvoiceRecord]) -> None:
        for record in records:
            original=record.original_data or self._snapshot(record); record.original_data=original; payload=_json(record.to_dict())
            existing=self.conn.execute("SELECT id FROM records WHERE (source_sha256 != '' AND source_sha256 = ?) OR (source_sha256 = '' AND source_file = ?) ORDER BY id DESC LIMIT 1",(record.source_sha256,record.source_file)).fetchone()
            if existing:
                record.record_id=int(existing[0]); self._update(record,payload)
            else:
                cursor=self.conn.execute("INSERT INTO records(source_file,source_sha256,invoice_number,status,original_payload,current_payload) VALUES(?,?,?,?,?,?)",(record.source_file,record.source_sha256,record.invoice_number,record.status.value,_json(original),payload)); record.record_id=cursor.lastrowid
            self._save_corrections(record)
        self.conn.commit()

    def _update(self, record: InvoiceRecord, payload: str) -> None:
        self.conn.execute("UPDATE records SET source_file=?,invoice_number=?,status=?,current_payload=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",(record.source_file,record.invoice_number,record.status.value,payload,record.record_id))

    def update(self, record: InvoiceRecord) -> None:
        if record.record_id is None: self.save([record]); return
        record.original_data=record.original_data or self._snapshot(record); self._update(record,_json(record.to_dict())); self._save_corrections(record); self.conn.commit()

    def _save_corrections(self, record: InvoiceRecord) -> None:
        if record.record_id is None: return
        self.conn.execute("DELETE FROM correction_history WHERE record_id=?",(record.record_id,))
        for correction in record.corrections:
            self.conn.execute("INSERT INTO correction_history(record_id,field_name,original_value,corrected_value,corrected_at) VALUES(?,?,?,?,?)",(record.record_id,correction.field_name,_json(correction.original_value),_json(correction.corrected_value),correction.timestamp))

    @staticmethod
    def _snapshot(record: InvoiceRecord) -> dict[str,Any]:
        data=record.to_dict(); data.pop("original_data",None); data.pop("corrections",None); data.pop("record_id",None); return data

    def load(self, limit: int=1000) -> list[InvoiceRecord]:
        rows=self.conn.execute("SELECT id,current_payload FROM records ORDER BY id ASC LIMIT ?",(limit,)).fetchall(); result=[]
        for row in rows:
            record=InvoiceRecord.from_dict(json.loads(row[1])); record.record_id=int(row[0]); result.append(record)
        return result

    def delete(self, record_id: int) -> None:
        self.conn.execute("DELETE FROM records WHERE id=?",(record_id,)); self.conn.commit()

    def backup_to(self, destination: str | Path) -> Path:
        """Create a consistent SQLite backup without modifying the live database."""
        destination=Path(destination); destination.parent.mkdir(parents=True, exist_ok=True); self.conn.commit()
        with sqlite3.connect(destination) as target: self.conn.backup(target)
        return destination

    @staticmethod
    def restore_from(backup: str | Path, destination: str | Path) -> Path:
        backup=Path(backup); destination=Path(destination)
        if not backup.is_file(): raise FileNotFoundError(backup)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(backup) as source, sqlite3.connect(destination) as target: source.backup(target)
        return destination

    def close(self): self.conn.close()
