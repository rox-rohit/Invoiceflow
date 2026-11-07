# InvoiceFlow 3.0.0

## Product experience foundation

- Added the 3.0 redesign audit and prioritized product-experience work.
- Added centralized brand/design tokens and improved teal/sage visual hierarchy.
- Added persisted collapsible sidebar navigation with accessible tooltips.
- Improved dark-theme navigation, primary actions and tooltip contrast.
- Rebuilt the 2.5.1 package path remains available for rollback and comparison.

# InvoiceFlow 2.5.1

## Professional Windows installer

- Added an Inno Setup installer for the complete PyInstaller onedir distribution.
- Added Start Menu integration, optional desktop shortcut, upgrade handling and registered uninstaller.
- User data remains in `%LOCALAPPDATA%\InvoiceFlow\history.db` and is preserved during upgrades and uninstall.
- Added installer SHA256 checksum generation and packaging validation documentation.

# InvoiceFlow 2.5.0

## Business operations completion

- Added persistent customer and supplier records with editing, deactivation, search and duplicate-safe constraints.
- Added import history with total, imported, rejected and duplicate row counts plus validation details.
- Added receivables and payables aging based on due dates and explicit payment allocations.
- Added functional Settings and Data Management pages with business profile, theme selection, storage statistics, SQLite integrity checks and verified backups/restores.
- Added first-launch onboarding for new local databases without interrupting existing users.
- Added additive database migration version 3 for contacts, settings and backup history.

# InvoiceFlow 2.4.3

## Brand identity and budget analytics

- Integrated the approved InvoiceFlow IF logo into the sidebar, application icon, taskbar/window icon and startup splash.
- Bundled the approved logo and multi-resolution Windows ICO in the onedir package.
- Added period-aware budget utilization calculations using verified operating expenses and overlapping budget periods.
- Added a dedicated Analytics budget utilization chart with category performance, remaining balances and overrun handling.

# InvoiceFlow 2.4.2

## Analytics visualization completion

- Added period-aware daily, weekly and monthly analytics aggregation.
- Rebuilt the Analytics page with data-backed KPI cards, grouped financial charts, expense-category visualization, cash-movement charts and revenue trends.
- Added consistent Analytics date controls and verified-record data-quality messaging.
- Fixed QtCharts rendering so refreshed charts display complete bar data immediately.
- Added chart drill-down callbacks while preserving the existing financial calculation service.

# InvoiceFlow 2.4.1

## Desktop UI/UX redesign

- Replaced the duplicated top-level navigation with a compact, grouped left navigation shell.
- Added scrollable page containers so long forms, tables and import workflows no longer clip or overlap.
- Added a shared visual system for surfaces, KPI cards, tables, forms, buttons, focus states and empty states.
- Rebuilt the home dashboard with financial KPIs, quick actions, performance charts and recent activity.
- Added a combined Transactions page while preserving all existing financial pages and handlers.
- Standardized table sizing, alternating rows, selection states and responsive stretch behavior.
- Updated the application version and About screen to 2.4.1.

# InvoiceFlow 2.4.0

- Added preview-first CSV/XLSX imports for sales, returns, purchases, expenses, collections and supplier payments.
- Added SHA-256 import-batch provenance and idempotent repeated-import protection.
- Added explicit payment allocations with partial-payment balances, reversal audit history and allocation limits.
- Added today, yesterday, week and month presets to the overview date selector.
- Reversals now retain the source transaction date so period reports remain traceable.
- Updated the displayed application version to 2.4.0.

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
