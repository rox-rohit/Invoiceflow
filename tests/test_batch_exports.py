import io, zipfile
from pathlib import Path
import pytest
from src.batch import safe_zip_extract
from src.exporter import export_csv, export_excel, export_json
from src.models import InvoiceRecord

def test_nested_zip_and_traversal(tmp_path):
    z=tmp_path/"x.zip"
    with zipfile.ZipFile(z,"w") as f: f.writestr("nested/a.pdf",b"pdf"); f.writestr("../escape.pdf",b"bad")
    with pytest.raises(ValueError): safe_zip_extract(z,tmp_path/"out")

def test_nested_zip_pdf_discovery(tmp_path):
    inner=io.BytesIO()
    with zipfile.ZipFile(inner,"w") as archive: archive.writestr("nested/invoice.pdf",b"%PDF-invalid")
    outer=tmp_path/"nested.zip"
    with zipfile.ZipFile(outer,"w") as archive: archive.writestr("folder/archive.zip",inner.getvalue())
    extracted=safe_zip_extract(outer,tmp_path/"out")
    assert len(extracted)==1 and extracted[0].read_bytes()==b"%PDF-invalid"

def test_exports(tmp_path):
    r=InvoiceRecord(invoice_number="A")
    export_csv([r],tmp_path/"a.csv"); export_json([r],tmp_path/"a.json"); export_excel([r],tmp_path/"a.xlsx")
    assert all((tmp_path/n).exists() for n in ["a.csv","a.json","a.xlsx"])
