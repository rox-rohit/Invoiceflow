# Troubleshooting

**A PDF is marked REQUIRES_OCR**: it is image-only or contains too little extractable text. OCR is not included in this release; use a text-based PDF export.

**A record is NEEDS_REVIEW**: the document was recognized, but a missing/ambiguous field or a financial reconciliation warning needs attention. Informational line arithmetic warnings may be shown without changing a sufficiently complete record to NEEDS_REVIEW.

**A file is ERROR**: the PDF could not be opened or processed. Password-protected, malformed and empty files are isolated from the rest of a batch.

**History is missing**: check `%LOCALAPPDATA%\InvoiceFlow\history.db`. Do not move the database into the installation folder.
