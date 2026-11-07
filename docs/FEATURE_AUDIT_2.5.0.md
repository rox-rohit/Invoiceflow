# InvoiceFlow 2.5.0 Feature Audit

This audit records implementation status from source inspection, focused regression tests, and native PySide6 smoke checks. A visible control is not classified as working unless its handler and persisted data path were verified.

| Area | Feature | Status | Evidence / limitation |
|---|---|---|---|
| Documents | PDF, bulk PDF and ZIP processing | WORKING | Background worker, bounded ZIP processing and existing regression coverage. |
| Documents | Extraction, classification, review and correction | WORKING | Existing deterministic parser and correction-history workflow. |
| Documents | Duplicate detection and exports | WORKING | Existing source/invoice duplicate checks and CSV/XLSX/JSON exports. |
| Financials | Sales, purchases, expenses, collections, payments, returns | WORKING | Verified ledger transaction types and existing forms/imports. |
| Financials | Editing, reversals and audit history | WORKING | Ledger update/reversal methods and transaction detail dialog. |
| Financials | Payment allocation and reversal | WORKING | Atomic allocation limits, allocation audit and reconciliation page. |
| Financials | Receivables/payables outstanding balances | WORKING | Allocation-based balances; aging now uses due dates and explicit allocations. |
| Analytics | KPIs, filters, aggregation and charts | WORKING | Central analytics service with daily/weekly/monthly QtCharts. |
| Analytics | Budget utilization | WORKING | Category chart based on saved active budgets and verified expenses. |
| Management | Customer/supplier records | WORKING | Persistent contacts migration, add/edit/deactivate path, search and unique role/name constraint. |
| Management | Import history | WORKING | Batch provenance, row counts, duplicate counts and validation details. |
| Management | Budgets and business insights | WORKING | Existing budget CRUD and deterministic insight calculations. |
| Application | Navigation, Back, search, sorting | WORKING | Sidebar navigation, page history, table sorting and transaction search. |
| Application | Settings and business profile | WORKING | Profile persistence, theme and storage statistics. |
| Application | Backup and integrity checks | WORKING | SQLite online backup, integrity validation and safety backup before restore. |
| Application | Restore failure recovery | PARTIALLY WORKING | Source validation and safety backup exist; restart is required after a successful restore. |
| Application | First-launch onboarding | WORKING | Non-modal setup dialog persists completion and does not create financial records. |
| Application | Light/dark/system themes | PARTIALLY WORKING | Central stylesheet switching is implemented and persists; OS theme detection is intentionally conservative. |
| Application | Pagination | NOT IMPLEMENTED | Current operational tables use scrolling and sorting rather than server-side pagination. |
| Application | Commercial readiness | NOT IMPLEMENTED | Requires real-business acceptance, installer/upgrade testing, backup restore drills and broader accounting validation. |
