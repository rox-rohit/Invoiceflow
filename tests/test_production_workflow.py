import json
import zipfile
from datetime import datetime, timezone

import pytest

fitz = pytest.importorskip("pymupdf")
from src.batch import process_batch
from src.exporter import export_csv, export_excel, export_json
from src.invoice_parser import parse_invoice
from src.models import Correction, InvoiceRecord, ProcessingStatus
from src.pdf_extractor import extract_pdf
from src.storage import HistoryStore
from src.job import JobState, JobStore

def make_pdf(path, text):
    doc=fitz.open(); page=doc.new_page(); page.insert_text((40,40),text); doc.save(path); doc.close()

def test_rich_invoice_fields_and_non_invoice(tmp_path):
    invoice=tmp_path/"rich.pdf"
    make_pdf(invoice,"""TAX INVOICE\nSeller: Acme Supplies\nGSTIN: 27ABCDE1234F1Z5\nInvoice Number: INV-2026/07\nInvoice Date: 07/11/2026\nDue Date: 21/11/2026\nBill To: Example Customer\nDescription Qty Rate Amount\nWidget A 2 10.00 20.00\nSubtotal: 20.00\nCGST: 1.80\nSGST: 1.80\nGrand Total: 23.60""")
    record=parse_invoice(extract_pdf(invoice))
    assert record.status in {ProcessingStatus.FOUND, ProcessingStatus.NEEDS_REVIEW}
    assert record.invoice_number == "INV-2026/07" and record.vendor_name == "Acme Supplies"
    assert record.cgst == 1.8 and record.sgst == 1.8 and record.total_amount == 23.6

def test_scanned_and_corrupt_isolated(tmp_path):
    scanned=tmp_path/"scanned.pdf"; doc=fitz.open(); doc.new_page(); doc.save(scanned); doc.close()
    result=process_batch([scanned,tmp_path/"broken.pdf"])
    assert {item.status for item in result} == {ProcessingStatus.REQUIRES_OCR, ProcessingStatus.ERROR}

def test_corrections_persist_and_original_remains(tmp_path):
    store=HistoryStore(tmp_path/"history.db")
    record=InvoiceRecord(source_file="a.pdf", invoice_number="OLD", status=ProcessingStatus.NEEDS_REVIEW)
    record.original_data=record.to_dict(); record.corrections=[Correction("invoice_number","OLD","NEW",datetime.now(timezone.utc).isoformat())]; record.invoice_number="NEW"; record.manually_corrected.add("invoice_number")
    store.save([record]); loaded=store.load()[0]; store.close()
    assert loaded.invoice_number == "NEW" and loaded.original_data["invoice_number"] == "OLD" and loaded.corrections[0].corrected_value == "NEW"

def test_database_backup_and_restore(tmp_path):
    source=HistoryStore(tmp_path/"source.db"); source.save([InvoiceRecord(invoice_number="BACKUP")]); backup=source.backup_to(tmp_path/"backup.db"); source.close()
    restored=tmp_path/"restored.db"; HistoryStore.restore_from(backup,restored); reopened=HistoryStore(restored)
    assert reopened.load()[0].invoice_number == "BACKUP"; reopened.close()

def test_exports_read_back_corrected_values(tmp_path):
    record=InvoiceRecord(invoice_number="CORRECTED", total_amount=99.5, status=ProcessingStatus.FOUND)
    export_json([record],tmp_path/"r.json"); export_csv([record],tmp_path/"r.csv"); export_excel([record],tmp_path/"r.xlsx")
    assert json.loads((tmp_path/"r.json").read_text(encoding="utf-8"))[0]["invoice_number"] == "CORRECTED"
    assert "CORRECTED" in (tmp_path/"r.csv").read_text(encoding="utf-8-sig")
    from openpyxl import load_workbook
    assert load_workbook(tmp_path/"r.xlsx",read_only=True)["Invoice Summary"].max_row == 2

def test_job_state_roundtrip(tmp_path):
    jobs=JobStore(tmp_path/"jobs"); state=JobState("batch-1",total=10,completed=3,completed_sources=["a.pdf"]); jobs.save(state)
    loaded=jobs.load("batch-1"); assert loaded.completed==3 and loaded.completed_sources==["a.pdf"]; jobs.clear("batch-1"); assert jobs.load("batch-1") is None

def test_batch_resume_skips_completed_sources(tmp_path):
    first=tmp_path/"a.pdf"; second=tmp_path/"b.pdf"
    make_pdf(first,"TAX INVOICE\nInvoice Number: A\nSeller: Vendor\nTotal: 10")
    make_pdf(second,"TAX INVOICE\nInvoice Number: B\nSeller: Vendor\nTotal: 20")
    jobs=JobStore(tmp_path/"jobs")
    jobs.save(JobState("resume",total=2,completed=1,completed_sources=[first.name]))
    results=process_batch([first,second],state_path=tmp_path/"jobs"/"state.json",job_id="resume",resume=True)
    assert len(results)==1 and results[0].source_file.endswith("b.pdf")
