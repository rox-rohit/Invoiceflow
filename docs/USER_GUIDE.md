# InvoiceFlow user guide

1. Open InvoiceFlow.
2. Choose one or more PDFs or a ZIP containing PDFs on **Process Invoices**.
3. Start processing and wait for the progress indicator.
4. Inspect **Results** and double-click a row to open the review editor.
5. Edit fields, add/remove line items, and choose Save. Original extracted values and correction history are retained.
6. Select rows before exporting to export only those rows; with no selection, all loaded records are exported.
7. Use **Review** to see missing or ambiguous fields and arithmetic warnings.
8. Export results from the Results screen.

## Reports

Open **Reports & Business Insights** and choose `month`, `last_6_months`, `last_12_months` or `year_to_date`. Reports use explicitly classified financial transactions. Invoice documents are not assumed to be cash collections or payments. For complete reports, classify or import sales, purchases, expenses, collections and payments; incomplete periods are identified in the report.

Text PDFs are supported. Scanned PDFs are reported as `REQUIRES_OCR`; no OCR is performed.

History is stored at `%LOCALAPPDATA%\InvoiceFlow\history.db`. Back up that file and the source PDFs separately; see `BACKUP_AND_RESTORE.md`.
