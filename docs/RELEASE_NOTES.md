# InvoiceFlow 2.2.0

## 2.2.0 — Stability, UX and analytics navigation

- Added card-based home navigation in the native desktop UI.
- Replaced manual report-period text entry with a visual period selector and calendar date control.
- Added worker lifecycle cleanup, close-time cancellation handling and throttled progress updates.
- Fixed resumable processing so completed sources are actually skipped.
- Added progressive synthetic batch-stability tooling for 1, 10, 25, 50, 100, 250 and 500 PDFs.
- Added regression coverage for batch resume and period-selector navigation.

The stress fixtures and throughput results are synthetic stability measurements, not extraction-accuracy evidence.

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
