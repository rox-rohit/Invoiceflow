# InvoiceFlow 2.1.0

InvoiceFlow is a native Windows desktop application for deterministic local processing of text-based PDF invoices.

## Features

- PySide6 desktop GUI with dashboard, processing, results and review views.
- PyMuPDF text and word-coordinate extraction, invoice classification, field parsing and line-item heuristics.
- Explicit `FOUND`, `NEEDS_REVIEW`, `REQUIRES_OCR`, `NOT_AN_INVOICE` and `ERROR` statuses.
- Safe PDF/ZIP batch processing with duplicate suppression, path traversal protection and bounded input sizes.
- Excel, CSV and JSON exports; SQLite history in `%LOCALAPPDATA%\\InvoiceFlow`.
- Editable review workflow for invoice fields and line items, with original-value snapshots and correction audit history.
- Duplicate source-document suppression and duplicate invoice-number warnings within a batch.
- V2 intelligence: weighted duplicate matching, field evidence, historical vendor-total anomaly alerts and verified correction-feedback export.
- Bounded 2,000-PDF directory/ZIP batch processing with temporary cleanup and resumable job state.
- Reports & Business Insights backend with monthly/rolling periods, traceable metrics, comparisons, targets, budgets and data-quality explanations.

Scanned PDFs are detected and marked as requiring OCR. OCR is intentionally not included. Extraction is deterministic and should be reviewed for unfamiliar invoice layouts; no claim is made that all real-world invoices are supported.

The parser supports common label variants including `Invoice no`, `Date of issue`, `Seller`, `Client`, `Net worth`, `VAT`, `Gross worth`, and separated vertical invoice-table headers. Ambiguous or unreconciled values remain visible as review warnings.

See `docs/V2_INTELLIGENCE.md` for the shipped intelligence features and deliberately deferred ML/OCR work. The current confidence signals are heuristic and explicitly uncalibrated.

## Development

Use a supported Python release (3.12 or 3.13 is recommended for PySide6/PyInstaller compatibility):

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python main.py
pytest -q
```

The current environment used for source inspection is Python 3.15; some binary dependencies may not yet publish wheels for that interpreter.

## Build Windows executable

From a supported Windows Python environment:

```powershell
powershell -ExecutionPolicy Bypass -File packaging\windows\build_windows.ps1
```

This creates `dist\\InvoiceFlow\\InvoiceFlow.exe` (onedir, preferred for reliable Qt startup). A one-file build can be enabled with `-OneFile`.

## Data and troubleshooting

History is stored outside the installation directory in `%LOCALAPPDATA%\\InvoiceFlow\\history.db`. ZIP processing only extracts PDFs, rejects traversal, and enforces 2,000 PDFs / 100 MB uncompressed by default. The application has no server, browser or network dependency.

The historical 1,018-PDF benchmark is not assumed to be present and was not used as a benchmark claim. Use `tools/benchmark.py` when the original corpus is available.

Customer handover documents are in `docs`: installation, user guide, troubleshooting, backup/restore, privacy, supported PDF types and release notes.

## Review and corrections

Double-click a result to open the correction dialog. Edit invoice fields, add/remove line items, save, and re-open the record after restarting. Current values are exported; original extraction and correction history remain in SQLite.
