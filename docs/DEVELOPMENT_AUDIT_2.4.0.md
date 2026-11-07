# InvoiceFlow 2.4.0 development audit

Audit date: 2026-11-07

## Current architecture

InvoiceFlow is a native PySide6 desktop application. PDF extraction and legacy invoice history remain in `src/storage.py` and the existing parser pipeline. The additive financial ledger is implemented in `src/ledger.py` in the same SQLite database, using Decimal values serialized as text. The GUI retains card-based home navigation and opens dedicated pages from `gui/main_window.py`.

## Working

- PDF and ZIP processing, duplicate source suppression, correction persistence and correction audit history.
- SQLite migration of the legacy invoice history and additive financial ledger.
- Explicit verification states and transaction audit records.
- Sales, purchases, expenses, collections and supplier payments as distinct transaction types.
- Decimal-safe analytics, reports, PDF/Excel/CSV/JSON report exports and financial-year period calculations.
- Manual transaction entry, explicit payment allocation, partial balances, allocation reversal and allocation limits.
- Preview-first CSV/XLSX import with column mapping, row validation, duplicate detection, SHA-256 provenance and repeated-file idempotency.
- Card-based dashboard, visual calendar controls, charts and global Back navigation.

## Partially implemented

- Import UI previews and confirms rows, but mapping preferences are not yet persisted between sessions and import history has no dedicated GUI page.
- Customer and supplier pages currently summarize ledger counterparties; they are not yet full contact records with separate editable master data.
- Charts open through source IDs in the analytics service, but the GUI does not yet provide a complete transaction drill-down dialog for every chart element.
- Receivables and payables are available through reconciliation balances, but there are no dedicated aging reports.
- Report exports are traceable through source IDs in the backend; the GUI export surface is not yet uniform across every report format.

## Missing or deferred

- OCR for scanned PDFs.
- Inventory valuation, opening/closing stock, payroll and statutory accounting.
- Full customer/supplier master-data CRUD and merge workflow.
- Dedicated import-history and outstanding-receivables/payables pages.

## Bugs found and fixed for 2.4.0

- Reversals were dated with the current date, which could leave the reversal outside the source report period. Reversals now retain the source transaction date and remain auditable.
- The new import reconciliation test referenced an undefined local variable; the test now uses an explicit report range.
- The overview omitted today, yesterday, this week, last week and last month presets.
- The displayed application version was still 2.3.1.

## Database and migration risks

- `LedgerStore.migrate()` is additive and repeatable, and preserves legacy `records` and correction history.
- The new import and allocation tables use foreign keys and are created in the same SQLite database.
- Existing databases should be backed up before upgrades. No migration deletes financial or invoice records.
- SQLite connections are currently owned by the calling page/service; long-running concurrent writes should continue to use short transactions.

## Test audit

The full suite initially could not create pytest's default Windows temporary directory because of an environment permission issue. Running with a writable project-local `--basetemp` completed 38 tests successfully and exposed two failures; both are addressed in this release work. The suite should be rerun with the project-local basetemp before packaging.

## Packaging

`dist/InvoiceFlow` exists, but its timestamp predates the 2.4.0 source changes. It must be rebuilt with `packaging/windows/build_windows.ps1` before distribution.
