# Supported PDF types and limitations

InvoiceFlow supports text-based PDF invoices, including common seller/customer labels, tax labels, summary layouts, wrapped descriptions, multi-line tables, ZIP batches and duplicate detection.

Image-only/scanned PDFs are detected and reported as `REQUIRES_OCR`; OCR is not implemented. Unfamiliar templates may produce `NEEDS_REVIEW`. The parser preserves extracted values and does not change amounts to force arithmetic reconciliation.

Non-invoice documents are classified as `NOT_AN_INVOICE`. Password-protected, empty or malformed PDFs are reported as `ERROR` or `REQUIRES_OCR` according to the failure type.
