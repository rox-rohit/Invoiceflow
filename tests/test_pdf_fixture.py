import pytest
fitz=pytest.importorskip("pymupdf")
from src.invoice_parser import parse_invoice
from src.pdf_extractor import extract_pdf

def test_synthetic_text_invoice(tmp_path):
    pdf=fitz.open(); page=pdf.new_page(); page.insert_text((40,40),"Acme Supplies\nInvoice Number: INV-42\nInvoice Date: 2026-11-07\nBill To: Example Customer\nDescription Qty Rate Amount\nWidget 2 10.00 20.00\nSubtotal 20.00\nTax 2.00\nGrand Total 22.00")
    path=tmp_path/"invoice.pdf"; pdf.save(path); pdf.close()
    result=parse_invoice(extract_pdf(path)); assert result.invoice_number=="INV-42"; assert result.total_amount==22.0
