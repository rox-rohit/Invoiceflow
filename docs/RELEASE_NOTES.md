# InvoiceFlow 2.3.1

## 2.3.1 — Workflow completion and navigation repair

- Added global Back buttons and a centralized navigation history.
- Added a dedicated Analytics home card and page.
- Added quick daily actions for sales, purchases, expenses, collections and payments.
- Added manual verified transaction entry using the unified financial ledger.
- Added Expenses, Money Received and Money Paid operational pages.
- Added transaction approval, audit-aware update/reversal service methods.
- Added navigation and manual-entry regression coverage.

CSV/Excel financial-data import, full contact management and complete payment allocation remain deferred until their schemas and validation rules are expanded.

## 2.3.0 — Business analytics and financial intelligence

- Added a centralized analytics service for verified KPI, monthly, category and party calculations.
- Added QtCharts revenue/expense and expense-category visualizations to Business Overview.
- Added extended date presets, configurable April–March financial-year periods and custom calendar ranges.
- Added functional verified Sales, Purchases & Expenses, Customers & Suppliers, Business Insights and Budgets & Targets pages.
- Added non-destructive budget activation/editing persistence.
- Added shareable PDF business-report export with explicit estimate and data-quality disclosures.
- Added analytics, chart, budget and PDF export regression coverage.

Analytics remain conservative: receivables/payables, definitive COGS and net profit require explicit supporting records.

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
