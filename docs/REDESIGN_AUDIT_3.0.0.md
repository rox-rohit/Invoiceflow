# InvoiceFlow 3.0.0 Product Redesign Audit

This audit is based on source inspection, the existing regression suite, and prior native GUI/package smoke tests. Status is intentionally conservative: a visible control is not classified as working unless its handler and persisted data path exist.

## Application shell and navigation

| Feature | Status | Finding |
|---|---|---|
| Native PySide6 shell | WORKING | `gui/main_window.py` builds a native `QMainWindow` and stacked pages. |
| Sidebar navigation | PARTIALLY WORKING | Navigation is functional, but the sidebar is fixed-width, duplicated for some destinations, and has no collapse state. |
| Back navigation | WORKING | Page history and Back action are implemented. |
| Responsive sizing | PARTIALLY WORKING | Minimum size is 900x680; some tables and dense controls remain wide at smaller sizes. |
| Global search | NOT IMPLEMENTED | Search exists only within selected workflows, not as a shell-level command/search experience. |
| Alerts/notification centre | NOT IMPLEMENTED | No persistent notification or actionable alert centre exists. |

## Dashboard and analytics

| Feature | Status | Finding |
|---|---|---|
| Verified KPI calculations | WORKING | Analytics uses verified ledger transactions and explicit data-quality notes. |
| Date-period controls | WORKING | Overview and Analytics provide predefined and custom periods. |
| Revenue/expense/cash charts | WORKING | QtCharts are data-backed and have empty states. |
| Budget utilization | WORKING | Budget chart uses saved budgets and eligible verified expense records. |
| Premium visual hierarchy | PARTIALLY WORKING | Existing cards and charts are functional but dense and visually inconsistent with the 3.0 target. |
| KPI comparisons | PARTIALLY WORKING | Comparisons are shown where prior-period values exist; no compact trend/sparkline layer exists. |
| Business insights | PARTIALLY WORKING | Deterministic anomaly/data-quality insights exist, but source evidence and action links are limited. |
| Empty-state guidance | PARTIALLY WORKING | Some pages provide explanatory empty states; dashboard actions and context are not consistently adaptive. |

## Financial operations

| Feature | Status | Finding |
|---|---|---|
| Manual sales, purchases, expenses, collections and payments | WORKING | Transaction dialog and ledger persistence exist. |
| Independent payment/collection entry | WORKING | Manual entry does not require an invoice. |
| Payment allocation/reconciliation | WORKING | Allocation limits, audit history and reversal safeguards exist. |
| Receivables/payables aging | WORKING | Due dates and explicit allocations drive aging. |
| Returns and reversals | WORKING | Existing ledger reversal/audit workflows remain available. |
| Product/item management | NOT IMPLEMENTED | No dedicated product catalogue page or persisted item master exists. |
| Large-table pagination/virtualization | NOT IMPLEMENTED | Tables rely on Qt scrolling and sorting. |

## Documents and imports

| Feature | Status | Finding |
|---|---|---|
| PDF, bulk and ZIP processing | WORKING | Existing worker and bounded archive processing are present. |
| Review and correction | WORKING | Extraction review and correction dialog paths exist. |
| CSV/XLSX imports | WORKING | Preview, mapping, validation, duplicate detection and idempotent confirmation exist. |
| Independent import types | PARTIALLY WORKING | Financial import types exist, but the import centre is not yet a unified multi-workflow workspace for every requested type. |
| Import history | WORKING | Provenance, row counts, duplicates and validation details are persisted and displayed. |
| Batch results workspace | PARTIALLY WORKING | Results exist, but batch-scoped visual analytics and line-item analysis are limited. |
| Smart categorization | PARTIALLY WORKING | Deterministic categories and correction history exist; confidence/evidence presentation is limited and no validated ML baseline is enabled. |

## Settings, onboarding and data safety

| Feature | Status | Finding |
|---|---|---|
| Business profile | WORKING | Profile persistence and Settings editing exist. |
| Backup/restore | WORKING | SQLite backup, integrity checks and safety backup before restore exist. |
| Onboarding | PARTIALLY WORKING | First-launch setup persists state, but it is a compact form rather than a resumable step-by-step wizard. |
| Light/dark/system theme | PARTIALLY WORKING | Central stylesheet switching exists, but it is replacement-based and needs full component contrast validation. |
| Upgrade-safe database path | WORKING | Database remains under `%LOCALAPPDATA%\\InvoiceFlow\\history.db`. |
| Export coverage | PARTIALLY WORKING | Core transaction/report exports exist; a unified export centre for every requested dataset is incomplete. |

## Packaging and release

| Feature | Status | Finding |
|---|---|---|
| PyInstaller onedir package | WORKING | 2.5.1 package builds and launches from another working directory. |
| Inno Setup installer | WORKING | Installer, checksum, upgrade and user-data-preserving uninstall were smoke-tested on the development host. |
| Clean-machine validation | NOT IMPLEMENTED | No clean Windows 10/11 machine or VM validation has been performed. |

## 3.0 priorities

1. Establish centralized design tokens and reliable light/dark chart styling.
2. Add a collapsible, persisted sidebar without exposing new placeholder pages.
3. Improve dashboard hierarchy and adaptive empty states using existing verified calculations.
4. Replace the compact onboarding form with a resumable wizard.
5. Consolidate independent imports and batch results without changing ledger semantics.
6. Validate every major workflow at 1280x875, 1024x768 and 900x680 before release.
