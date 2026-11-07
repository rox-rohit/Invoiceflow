# InvoiceFlow 2.1.0

## 2.1.0 — Financial Intelligence Foundation

- Added a versioned SQLite financial ledger alongside the legacy invoice history.
- Added Decimal-safe transaction amounts, explicit verification states and audit records.
- Added traceable period reports, budget-overrun insights and business-health data-quality indicators.
- Added report JSON, CSV and Excel exports using current calculated values.
- Added tests for ledger persistence, explicit invoice-to-transaction proposals and Decimal reporting.

This release does not claim full accounting, OCR, payroll, inventory valuation or machine-learning support.

## Included

- Native PySide6 desktop workflow.
- Deterministic PyMuPDF extraction and explicit processing statuses.
- Common invoice fields, taxes, totals and line items.
- Safe ZIP processing, duplicate source suppression and duplicate invoice warnings.
- SQLite history with migration support, original snapshots and correction audit history.
- Editable invoice review with line-item changes.
- Excel, CSV and JSON exports using current saved values.
- Onedir PyInstaller distribution.

## Known limitations

- OCR is not included.
- Template-specific extraction may require review.
- Inno Setup is not included in this environment.
- Clean-machine and installer upgrade testing require a separate Windows test machine.
