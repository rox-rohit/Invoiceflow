from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QDate, QThread
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (QComboBox, QDateEdit, QFileDialog, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMessageBox, QPushButton, QProgressBar, QStackedWidget, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from src.anomaly import detect_anomalies
from src.config import APP_NAME, DB_PATH
from src.duplicate import detect_duplicates
from src.exporter import export_csv, export_excel, export_json
from src.financials import transactions_from_invoices
from src.ledger import LedgerStore
from src.models import ProcessingStatus
from src.reports import build_report, period_for
from src.storage import HistoryStore
from .styles import STYLE
from .widgets import InvoiceEditDialog
from .workers import BatchWorker


class MainWindow(QMainWindow):
    """Native desktop shell with a card-based home screen and functional pages."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} — PDF invoices → structured data")
        self.setMinimumSize(1050, 680)
        self.records = []
        self.store = HistoryStore(DB_PATH)
        self.thread = None
        self.worker = None
        self._build()
        self._refresh()

    def _build(self):
        self.setStyleSheet(STYLE)
        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(24, 18, 24, 18)
        header = QHBoxLayout()
        header.addWidget(QLabel("InvoiceFlow", objectName="brand"))
        header.addWidget(QLabel("PDF invoices → structured data", objectName="tagline"))
        header.addStretch()
        self.location = QLabel("Home", objectName="breadcrumb")
        header.addWidget(self.location)
        home = QPushButton("Home")
        home.clicked.connect(lambda: self._navigate("Home"))
        header.addWidget(home)
        layout.addLayout(header)
        self.stack = QStackedWidget()
        layout.addWidget(self.stack, 1)
        self.setCentralWidget(root)

        self.home = self._home()
        self.process = self._process()
        self.results = self._results()
        self.review = self._review()
        self.reports = self._reports()
        self.settings = self._simple("Settings & Data", "Application data is stored in your Windows local application data folder.\n\nNo invoice contents leave this computer.")
        self.about = self._simple("About InvoiceFlow", "InvoiceFlow 2.2\nPDF invoices → structured data\n\nDeterministic local invoice processing with transparent review flags.")
        self.overview = self._overview()
        self.sales = self._simple("Sales & Income", "Sales, returns and collections become available after transactions are explicitly verified.")
        self.purchases = self._simple("Purchases & Expenses", "Purchases, expenses and supplier payments become available after transactions are explicitly verified.")
        self.parties = self._simple("Customers & Suppliers", "Customer and supplier history is derived from saved, verified records.")
        self.insights = self._simple("Business Insights", "Insights are generated from available verified records. No conclusion is shown when the supporting data is incomplete.")
        for widget in (self.home, self.process, self.results, self.review, self.reports, self.settings, self.about, self.overview, self.sales, self.purchases, self.parties, self.insights):
            self.stack.addWidget(widget)
        # Compatibility handle for existing integrations/tests; these are home cards, not a sidebar.
        self.nav = self.home_cards
        self._navigate("Home")

    def _page(self, title, explanation=""):
        widget = QWidget(); view = QVBoxLayout(widget); view.setContentsMargins(12, 4, 12, 12)
        view.addWidget(QLabel(title, objectName="pageTitle"))
        if explanation:
            note = QLabel(explanation, objectName="pageExplanation"); note.setWordWrap(True); view.addWidget(note)
        return widget, view

    def _simple(self, title, text):
        widget, view = self._page(title, text); view.addStretch(); return widget

    def _card(self, title, description, page):
        card = QPushButton(f"{title}\n{description}", objectName="featureCard")
        card.setMinimumHeight(128); card.setToolTip(description)
        card.clicked.connect(lambda checked=False, target=page: self._navigate(target))
        return card

    def _home(self):
        widget, view = self._page("Welcome to InvoiceFlow", "Choose what you want to do. Your financial totals are calculated from saved records and show their date range and data limitations.")
        self.stats = QLabel(objectName="overviewCard"); self.stats.setWordWrap(True); view.addWidget(self.stats)
        grid = QGridLayout(); grid.setSpacing(14)
        cards = [("Business Overview", "Revenue, expenses, cash movement and data completeness.", "Overview"), ("Invoices & Documents", "Import PDFs, process batches, review and correct extraction.", "Process Invoices"), ("Sales & Income", "Sales, returns and verified customer collections.", "Sales"), ("Purchases & Expenses", "Purchases, expenses and supplier payments.", "Purchases"), ("Reports & Analytics", "Period reports, comparisons, targets and exports.", "Reports"), ("Customers & Suppliers", "Parties, history and outstanding records.", "Customers & Suppliers"), ("Business Insights", "Explainable warnings based on available records.", "Business Insights"), ("Settings & Data", "Backup, restore, preferences and application data.", "Settings")]
        self.home_cards = []
        for index, (title, description, page) in enumerate(cards):
            card = self._card(title, description, page); self.home_cards.append(card); grid.addWidget(card, index // 2, index % 2)
        view.addLayout(grid); view.addStretch(); return widget

    def _overview(self):
        widget, view = self._page("Business Overview", "Verified transactions only. If a figure is unavailable, InvoiceFlow explains which records are missing.")
        self.overview_text = QLabel(objectName="overviewCard"); self.overview_text.setWordWrap(True); view.addWidget(self.overview_text); view.addStretch(); return widget

    def _process(self):
        widget, view = self._page("Invoices & Documents", "Import PDF files or ZIP archives. Processing runs in the background and isolates individual failures.")
        self.selected = QLabel("Choose PDF or ZIP files below."); view.addWidget(self.selected)
        row = QHBoxLayout(); choose = QPushButton("Choose files"); choose.clicked.connect(self._choose); clear = QPushButton("Clear"); clear.clicked.connect(lambda: self._set_files([])); row.addWidget(choose); row.addWidget(clear); row.addStretch(); view.addLayout(row)
        self.progress = QProgressBar(); self.current = QLabel(); view.addWidget(self.progress); view.addWidget(self.current)
        self.start = QPushButton("Start Processing", objectName="primary"); self.start.clicked.connect(self._start); self.cancel = QPushButton("Cancel"); self.cancel.setEnabled(False); self.cancel.clicked.connect(self._cancel); view.addWidget(self.start); view.addWidget(self.cancel); view.addStretch(); self.files = []; return widget

    def _results(self):
        widget, view = self._page("Results", "Search, inspect and export the records produced by InvoiceFlow.")
        row = QHBoxLayout(); self.search = QLineEdit(); self.search.setPlaceholderText("Search invoice number, vendor or filename"); self.search.textChanged.connect(self._refresh_table); row.addWidget(self.search)
        for label, kind in (("Export Excel", "xlsx"), ("Export CSV", "csv"), ("Export JSON", "json")):
            export = QPushButton(label); export.clicked.connect(lambda checked=False, selected_kind=kind: self._export(selected_kind)); row.addWidget(export)
        view.addLayout(row); self.table = QTableWidget(0, 8); self.table.setHorizontalHeaderLabels(["Invoice Number", "Vendor", "Date", "Subtotal", "Tax", "Total", "Status", "Source File"]); self.table.setSelectionBehavior(QTableWidget.SelectRows); self.table.cellDoubleClicked.connect(self._detail); view.addWidget(self.table); return widget

    def _review(self):
        widget, view = self._page("Review", "Open a result to correct fields or explicitly verify it as a financial transaction.")
        self.review_text = QLabel("No records require review."); self.review_text.setWordWrap(True); view.addWidget(self.review_text); view.addStretch(); return widget

    def _reports(self):
        widget, view = self._page("Reports & Analytics", "Select a reporting period visually. Reports use verified ledger transactions when available.")
        controls = QHBoxLayout(); self.report_period = QComboBox()
        for label, kind in (("This month", "month"), ("This week", "week"), ("Today", "day"), ("Last 6 months", "last_6_months"), ("Last 12 months", "last_12_months"), ("Year to date", "year_to_date"), ("Calendar year", "calendar_year")): self.report_period.addItem(label, kind)
        self.report_anchor = QDateEdit(QDate.currentDate()); self.report_anchor.setCalendarPopup(True); self.report_anchor.setDisplayFormat("dd MMM yyyy")
        generate = QPushButton("Generate report", objectName="primary"); generate.clicked.connect(self._generate_report)
        controls.addWidget(QLabel("Period")); controls.addWidget(self.report_period); controls.addWidget(QLabel("As of")); controls.addWidget(self.report_anchor); controls.addWidget(generate); controls.addStretch(); view.addLayout(controls)
        self.report_output = QLabel("Select a period and generate a report."); self.report_output.setWordWrap(True); self.report_output.setObjectName("overviewCard"); view.addWidget(self.report_output); view.addStretch(); return widget

    def _navigate(self, label):
        pages = {"Home": (self.home, "Home"), "Overview": (self.overview, "Business Overview"), "Process Invoices": (self.process, "Invoices & Documents"), "Results": (self.results, "Results"), "Review": (self.review, "Review"), "Reports": (self.reports, "Reports & Analytics"), "Settings": (self.settings, "Settings & Data"), "About": (self.about, "About InvoiceFlow"), "Sales": (self.sales, "Sales & Income"), "Purchases": (self.purchases, "Purchases & Expenses"), "Customers & Suppliers": (self.parties, "Customers & Suppliers"), "Business Insights": (self.insights, "Business Insights")}
        widget, title = pages[label]; self.stack.setCurrentWidget(widget); self.location.setText(title); self._refresh()

    def _generate_report(self):
        try:
            period = period_for(self.report_period.currentData(), self.report_anchor.date().toPython()); ledger = LedgerStore(DB_PATH); transactions = ledger.list(verified_only=True); ledger.close()
            if not transactions:
                records = self.store.load(); explicit = {r.record_id: r.invoice_type for r in records if r.invoice_type in {"sale", "purchase", "expense", "collection", "payment"}}; transactions = transactions_from_invoices(records, explicit)
            report = build_report(transactions, period, "INR"); metrics = "\n".join(f"{metric.name}: {metric.value:,.2f} {metric.currency}" for metric in report.metrics.values() if metric.value is not None); notes = "\n".join(report.data_quality) or "Data quality checks passed for available records."; self.report_output.setText(f"{report.period.label}\n\n{metrics}\n\n{notes}")
        except Exception as exc: self.report_output.setText(f"Unable to generate report: {exc}")

    def _choose(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Select invoice PDFs or ZIP files", str(Path.home()), "Invoices (*.pdf *.zip)"); self._set_files(files)

    def _set_files(self, files):
        self.files = files; self.selected.setText(f"{len(files)} input file(s) selected"); self.start.setEnabled(bool(files))

    def _start(self):
        if self.thread and self.thread.isRunning(): return
        self.start.setEnabled(False); self.cancel.setEnabled(True); self.progress.setValue(0); self.thread = QThread(self); self.worker = BatchWorker(self.files); self.worker.moveToThread(self.thread); self.thread.started.connect(self.worker.run)
        self.worker.progress.connect(lambda current, total, name: (self.progress.setMaximum(total), self.progress.setValue(current), self.current.setText(f"{current}/{total}: {name}"))); self.worker.result.connect(self._save_incremental); self.worker.finished.connect(self._finished); self.worker.failed.connect(self._processing_failed); self.worker.finished.connect(self.thread.quit); self.worker.failed.connect(self.thread.quit); self.thread.finished.connect(self.worker.deleteLater); self.thread.finished.connect(self.thread.deleteLater); self.thread.start()

    def _cancel(self):
        if self.worker: self.worker.cancel(); self.current.setText("Cancellation requested; finishing active documents...")

    def _processing_failed(self, message):
        self.start.setEnabled(True); self.cancel.setEnabled(False); QMessageBox.critical(self, "Processing error", message)

    def _save_incremental(self, record): self.store.save([record])

    def _finished(self, records):
        history = self.store.load(); records = detect_duplicates(records, history); self.records = [detect_anomalies(record, history) for record in records]; self.store.save(self.records); self.start.setEnabled(True); self.cancel.setEnabled(False); self._refresh(); self._navigate("Results")

    def _refresh(self):
        try: self.records = self.store.load()
        except Exception: return
        counts = {status: sum(r.status == status for r in self.records) for status in ProcessingStatus}; total = sum((r.total_amount or 0) for r in self.records); summary = f"Records: {len(self.records)}   |   Found: {counts[ProcessingStatus.FOUND]}   |   Needs review: {counts[ProcessingStatus.NEEDS_REVIEW]}   |   Requires OCR: {counts[ProcessingStatus.REQUIRES_OCR]}   |   Errors: {counts[ProcessingStatus.ERROR]}\nInvoice totals in saved records: {total:,.2f} (source totals, not confirmed cash collections)"
        if hasattr(self, "stats"): self.stats.setText(summary)
        if hasattr(self, "overview_text"): self.overview_text.setText(summary + "\n\nOpen Reports & Analytics for a date-bounded financial view.")
        if hasattr(self, "table"): self._refresh_table()
        if hasattr(self, "review_text"): self.review_text.setText("\n".join(f"{r.invoice_number or '(missing number)'} — {issue.message}" for r in self.records if r.status == ProcessingStatus.NEEDS_REVIEW for issue in r.issues) or "No records require review.")

    def _refresh_table(self):
        term = self.search.text().lower() if hasattr(self, "search") else ""; rows = [r for r in self.records if not term or term in (r.invoice_number + r.vendor_name + r.source_file).lower()]; self.table.setRowCount(len(rows))
        for row_index, record in enumerate(rows):
            values = [record.invoice_number, record.vendor_name, record.invoice_date, "" if record.subtotal is None else f"{record.subtotal:,.2f}", "" if record.tax_amount is None else f"{record.tax_amount:,.2f}", "" if record.total_amount is None else f"{record.total_amount:,.2f}", record.status.value, Path(record.source_file).name]
            for column, value in enumerate(values): self.table.setItem(row_index, column, QTableWidgetItem(str(value)))
        self.table.resizeColumnsToContents()

    def _detail(self, row, _column):
        matches = [record for record in self.records if record.invoice_number == self.table.item(row, 0).text() and Path(record.source_file).name == self.table.item(row, 7).text()]
        if not matches: return
        record = matches[0]; dialog = InvoiceEditDialog(record, self)
        if dialog.exec():
            self.store.update(record)
            if dialog.transaction_type:
                ledger = LedgerStore(DB_PATH); existing = [item for item in ledger.list() if item.source_record_id == record.record_id and item.transaction_type == dialog.transaction_type]
                if not existing:
                    proposal = ledger.propose_from_invoice(record, dialog.transaction_type); proposal.verification_status = "VERIFIED"; ledger.add(proposal)
                ledger.close()
            self._refresh()

    def _export(self, kind):
        path, _ = QFileDialog.getSaveFileName(self, "Export results", str(Path.home() / f"invoiceflow_export.{kind}"), f"{kind.upper()} (*.{kind})")
        if not path: return
        try:
            selected = []
            for index in self.table.selectionModel().selectedRows() if hasattr(self, "table") else []:
                number = self.table.item(index.row(), 0).text(); source = self.table.item(index.row(), 7).text(); selected.extend(record for record in self.records if record.invoice_number == number and Path(record.source_file).name == source)
            records = selected or self.records; (export_excel if kind == "xlsx" else export_csv if kind == "csv" else export_json)(records, path); QMessageBox.information(self, "Export complete", f"Saved {len(records)} invoice(s) to {path}")
        except Exception as exc: QMessageBox.critical(self, "Export failed", str(exc))

    def closeEvent(self, event: QCloseEvent):
        if self.worker and self.thread and self.thread.isRunning():
            self.worker.cancel()
            if not self.thread.wait(8000):
                QMessageBox.warning(self, "Processing still active", "Please wait for the active PDF operation to finish before closing InvoiceFlow."); event.ignore(); return
        self.store.close(); event.accept()
