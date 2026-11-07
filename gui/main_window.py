from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QDate, QThread
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (QComboBox, QDateEdit, QFileDialog, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMessageBox, QPushButton, QProgressBar, QStackedWidget, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from src.anomaly import detect_anomalies
from src.analytics import build_analytics
from src.config import APP_NAME, DB_PATH
from src.duplicate import detect_duplicates
from src.exporter import export_csv, export_excel, export_json
from src.financials import transactions_from_invoices
from src.ledger import LedgerStore
from src.models import ProcessingStatus
from src.reports import build_report, period_between, period_for, previous_period
from src.report_exporter import export_report_pdf
from src.storage import HistoryStore
from .styles import STYLE
from .widgets import InvoiceEditDialog
from .workers import BatchWorker
from .charts import FinancialChart
from .transaction_dialog import TransactionDialog


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
        self._navigation=[]
        self._current_page="Home"
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
        home.clicked.connect(lambda: self._navigate("Home",False))
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
        self.budgets = self._budget_page()
        self.settings = self._simple("Settings & Data", "Application data is stored in your Windows local application data folder.\n\nNo invoice contents leave this computer.")
        self.about = self._simple("About InvoiceFlow", "InvoiceFlow 2.3.1\nPDF invoices → structured data\n\nDeterministic local invoice processing with transparent review flags.")
        self.overview = self._overview()
        self.analytics = self._analytics_page()
        self.sales = self._transaction_page("Sales & Income", {"sale", "sales_return", "collection"}, "sales")
        self.purchases = self._transaction_page("Purchases & Expenses", {"purchase", "purchase_return", "expense", "payment", "supplier_payment"}, "purchases")
        self.expenses = self._transaction_page("Expenses", {"expense"}, "expenses")
        self.received = self._transaction_page("Money Received", {"collection"}, "received")
        self.paid = self._transaction_page("Money Paid", {"payment", "supplier_payment"}, "paid")
        self.parties = self._party_page()
        self.insights = self._insights_page()
        for widget in (self.home, self.process, self.results, self.review, self.reports, self.budgets, self.settings, self.about, self.overview, self.analytics, self.sales, self.purchases, self.expenses, self.received, self.paid, self.parties, self.insights):
            self.stack.addWidget(widget)
        # Compatibility handle for existing integrations/tests; these are home cards, not a sidebar.
        self.nav = self.home_cards
        self._navigate("Home",False)

    def _page(self, title, explanation=""):
        widget = QWidget(); view = QVBoxLayout(widget); view.setContentsMargins(12, 4, 12, 12)
        header=QHBoxLayout(); back=QPushButton("← Back",objectName="backButton"); back.clicked.connect(self._back); header.addWidget(back); header.addWidget(QLabel(title, objectName="pageTitle")); header.addStretch(); view.addLayout(header)
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
        quick=QHBoxLayout()
        for label,kind in (("Add Sale","sale"),("Add Purchase","purchase"),("Add Expense","expense"),("Record Collection","collection"),("Record Payment","supplier_payment"),("Add Transaction","adjustment"),("Upload Documents","upload")):
            button=QPushButton(label,objectName="primary" if kind in {"sale","expense"} else ""); button.clicked.connect(lambda checked=False, value=kind: self._quick_action(value)); quick.addWidget(button)
        view.addLayout(quick)
        grid = QGridLayout(); grid.setSpacing(14)
        cards = [("Business Overview", "Revenue, expenses, cash movement and data completeness.", "Overview"), ("Invoices & Documents", "Import PDFs, process batches, review and correct extraction.", "Process Invoices"), ("Analytics", "Explore financial performance, sales, expenses and cash movement.", "Analytics"), ("Sales & Income", "Sales, returns and verified customer collections.", "Sales"), ("Purchases & Expenses", "Purchases, expenses and supplier payments.", "Purchases"), ("Expenses", "Record and review operating expenses by category.", "Expenses"), ("Money Received", "Record customer collections separately from sales.", "Money Received"), ("Money Paid", "Record supplier and other payments separately from purchases.", "Money Paid"), ("Reports & Analytics", "Period reports, comparisons, targets and exports.", "Reports"), ("Budgets & Targets", "Plan spending and compare actual verified transactions.", "Budgets"), ("Customers & Suppliers", "Parties, history and outstanding records.", "Customers & Suppliers"), ("Business Insights", "Explainable warnings based on available records.", "Business Insights"), ("Settings & Data", "Backup, restore, preferences and application data.", "Settings")]
        self.home_cards = []
        for index, (title, description, page) in enumerate(cards):
            card = self._card(title, description, page); self.home_cards.append(card); grid.addWidget(card, index // 2, index % 2)
        view.addLayout(grid); view.addStretch(); return widget

    def _quick_action(self, kind):
        if kind == "upload": self._navigate("Process Invoices")
        else: self._open_transaction(kind)

    def _overview(self):
        widget, view = self._page("Business Overview", "Verified transactions only. If a figure is unavailable, InvoiceFlow explains which records are missing.")
        controls = QHBoxLayout(); self.overview_period = QComboBox()
        for label, kind in (("This month", "month"), ("Last 3 months", "last_3_months"), ("Last 6 months", "last_6_months"), ("Last 12 months", "last_12_months"), ("Year to date", "year_to_date"), ("Current financial year", "current_financial_year"), ("Custom range", "custom")): self.overview_period.addItem(label, kind)
        self.overview_anchor = QDateEdit(QDate.currentDate()); self.overview_anchor.setCalendarPopup(True); self.overview_anchor.setDisplayFormat("dd MMM yyyy")
        self.overview_start = QDateEdit(QDate.currentDate().addMonths(-1)); self.overview_start.setCalendarPopup(True); self.overview_start.setDisplayFormat("dd MMM yyyy"); self.overview_start.setVisible(False)
        refresh = QPushButton("Refresh overview", objectName="primary"); refresh.clicked.connect(self._refresh_overview)
        self.overview_period.currentIndexChanged.connect(lambda _index: self.overview_start.setVisible(self.overview_period.currentData() == "custom"))
        controls.addWidget(QLabel("Period")); controls.addWidget(self.overview_period); controls.addWidget(QLabel("As of")); controls.addWidget(self.overview_anchor); controls.addWidget(self.overview_start); controls.addWidget(refresh); controls.addStretch(); view.addLayout(controls)
        self.overview_text = QLabel(objectName="overviewCard"); self.overview_text.setWordWrap(True); view.addWidget(self.overview_text)
        charts = QGridLayout(); self.revenue_chart = FinancialChart("Revenue vs expenses"); self.expense_chart = FinancialChart("Expense categories"); charts.addWidget(self.revenue_chart, 0, 0); charts.addWidget(self.expense_chart, 0, 1); view.addLayout(charts); view.addStretch(); return widget

    def _analytics_page(self):
        widget, view = self._page("Analytics", "A dedicated view of verified financial activity. Use the same period controls as Business Overview.")
        self.analytics_text=QLabel("Select Refresh to load analytics.",objectName="overviewCard"); self.analytics_text.setWordWrap(True); view.addWidget(self.analytics_text)
        charts=QGridLayout(); self.analytics_revenue_chart=FinancialChart("Monthly sales and expenses"); self.analytics_expense_chart=FinancialChart("Expense categories"); charts.addWidget(self.analytics_revenue_chart,0,0); charts.addWidget(self.analytics_expense_chart,0,1); view.addLayout(charts); refresh=QPushButton("Refresh analytics",objectName="primary"); refresh.clicked.connect(self._refresh_analytics); view.addWidget(refresh); view.addStretch(); return widget

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

    def _transaction_page(self, title, kinds, key):
        widget, view = self._page(title, "Only verified financial transactions are listed. Invoice documents alone are not treated as cash movement.")
        controls = QHBoxLayout(); search = QLineEdit(); search.setPlaceholderText("Search counterparty, reference or category"); add_button=QPushButton("Add transaction",objectName="primary"); add_button.clicked.connect(lambda checked=False, default=self._default_transaction_type(key): self._open_transaction(default)); export_csv_button = QPushButton("Export CSV"); export_xlsx_button = QPushButton("Export Excel")
        controls.addWidget(search); controls.addWidget(add_button); controls.addWidget(export_csv_button); controls.addWidget(export_xlsx_button); view.addLayout(controls)
        table = QTableWidget(0, 7); table.setHorizontalHeaderLabels(["Date", "Type", "Counterparty", "Category", "Amount", "Payment status", "Source"]); table.setSelectionBehavior(QTableWidget.SelectRows); view.addWidget(table)
        setattr(self, f"{key}_table", table); setattr(self, f"{key}_search", search); setattr(self, f"{key}_kinds", kinds)
        search.textChanged.connect(lambda _text, page_key=key: self._refresh_transaction_page(page_key)); export_csv_button.clicked.connect(lambda checked=False, page_key=key: self._export_transactions(page_key, "csv")); export_xlsx_button.clicked.connect(lambda checked=False, page_key=key: self._export_transactions(page_key, "xlsx")); table.cellDoubleClicked.connect(lambda row, column, page_key=key: self._transaction_detail(page_key, row, column))
        return widget

    @staticmethod
    def _default_transaction_type(key):
        return {"sales":"sale","purchases":"purchase","expenses":"expense","received":"collection","paid":"supplier_payment"}.get(key,"adjustment")

    def _open_transaction(self, default_type="sale"):
        dialog=TransactionDialog(default_type,self)
        if dialog.exec():
            try:
                ledger=LedgerStore(DB_PATH); ledger.add(dialog._transaction); ledger.close(); self._refresh()
            except Exception as exc: QMessageBox.critical(self,"Transaction not saved",str(exc))

    def _party_page(self):
        widget, view = self._page("Customers & Suppliers", "Totals are based on verified sales and purchases. Outstanding balances require explicit payment records and are not inferred from invoices alone.")
        self.party_text = QLabel(); self.party_text.setWordWrap(True); view.addWidget(self.party_text)
        self.party_table = QTableWidget(0, 4); self.party_table.setHorizontalHeaderLabels(["Party", "Role", "Value", "Source records"]); view.addWidget(self.party_table); view.addStretch(); return widget

    def _insights_page(self):
        widget, view = self._page("Business Insights", "These are deterministic findings based on verified records, not fraud conclusions or generic AI advice.")
        self.insight_text = QLabel("No insights are available until verified transactions exist."); self.insight_text.setWordWrap(True); view.addWidget(self.insight_text); view.addStretch(); return widget

    def _refresh_parties_and_insights(self):
        ledger = LedgerStore(DB_PATH); transactions = ledger.list(verified_only=True); ledger.close()
        period = period_for("last_12_months")
        snapshot = build_analytics(transactions, period, "INR", previous_period(period))
        rows = [(item["name"], "Customer", item["amount"], len(item["source_ids"])) for item in snapshot.customers] + [(item["name"], "Supplier", item["amount"], len(item["source_ids"])) for item in snapshot.suppliers]
        self.party_table.setRowCount(len(rows))
        self.party_text.setText(f"Customers: {len(snapshot.customers)}   Suppliers: {len(snapshot.suppliers)}   Period: {period.label}")
        for row, values in enumerate(rows):
            for column, value in enumerate(values): self.party_table.setItem(row, column, QTableWidgetItem(f"{value:,.2f}" if isinstance(value, (int, float)) else str(value)))
        self.party_table.resizeColumnsToContents()
        if snapshot.insights:
            self.insight_text.setText("\n\n".join(f"• {item['finding']}\nEvidence: {item['evidence']}\nSuggested action: {item['action']}\nConfidence: {item['confidence']}" for item in snapshot.insights))
        elif snapshot.data_quality:
            self.insight_text.setText("No actionable insights are available.\n\nData quality:\n• " + "\n• ".join(snapshot.data_quality))

    def _page_transactions(self, key):
        ledger = LedgerStore(DB_PATH); items = [item for item in ledger.list(verified_only=True) if item.transaction_type in getattr(self, f"{key}_kinds")]; ledger.close()
        term = getattr(self, f"{key}_search").text().casefold(); return [item for item in items if not term or term in " ".join((item.counterparty, item.reference_number, item.category, item.description)).casefold()]

    def _refresh_transaction_page(self, key):
        table = getattr(self, f"{key}_table"); items = self._page_transactions(key); table.setRowCount(len(items))
        for row, item in enumerate(items):
            values = [item.transaction_date, item.transaction_type.replace("_", " ").title(), item.counterparty or "—", item.category or "—", "" if item.amount is None else f"{item.amount:,.2f} {item.currency}", item.payment_status, Path(item.source_file).name if item.source_file else "—"]
            for column, value in enumerate(values): table.setItem(row, column, QTableWidgetItem(str(value)))
        table.resizeColumnsToContents()

    def _transaction_detail(self, key, row, _column):
        items = self._page_transactions(key)
        if row >= len(items): return
        item = items[row]; QMessageBox.information(self, "Transaction details", f"Transaction ID: {item.transaction_id}\nType: {item.transaction_type}\nDate: {item.transaction_date}\nAmount: {item.amount} {item.currency}\nCounterparty: {item.counterparty or 'Not recorded'}\nCategory: {item.category or 'Not recorded'}\nPayment status: {item.payment_status}\nVerification: {item.verification_status}\nSource: {item.source_file or 'Not recorded'}")

    def _export_transactions(self, key, extension):
        items = self._page_transactions(key); path, _ = QFileDialog.getSaveFileName(self, "Export transactions", str(Path.home() / f"invoiceflow_{key}.{extension}"), f"{extension.upper()} (*.{extension})")
        if not path: return
        try:
            if extension == "csv":
                import csv
                with Path(path).open("w", newline="", encoding="utf-8-sig") as stream:
                    writer = csv.writer(stream); writer.writerow(["transaction_id", "date", "type", "counterparty", "category", "amount", "currency", "payment_status", "source_file"])
                    for item in items: writer.writerow([item.transaction_id, item.transaction_date, item.transaction_type, item.counterparty, item.category, item.amount, item.currency, item.payment_status, item.source_file])
            else:
                from openpyxl import Workbook
                workbook = Workbook(); sheet = workbook.active; sheet.title = "Transactions"; sheet.append(["Transaction ID", "Date", "Type", "Counterparty", "Category", "Amount", "Currency", "Payment status", "Source file"])
                for item in items: sheet.append([item.transaction_id, item.transaction_date, item.transaction_type, item.counterparty, item.category, float(item.amount) if item.amount is not None else None, item.currency, item.payment_status, item.source_file])
                sheet.freeze_panes = "A2"; sheet.auto_filter.ref = sheet.dimensions; workbook.save(path)
            QMessageBox.information(self, "Export complete", f"Saved {len(items)} transaction(s) to {path}")
        except Exception as exc: QMessageBox.critical(self, "Export failed", str(exc))

    def _reports(self):
        widget, view = self._page("Reports & Analytics", "Select a reporting period visually. Reports use verified ledger transactions when available.")
        controls = QHBoxLayout(); self.report_period = QComboBox()
        for label, kind in (("This month", "month"), ("This week", "week"), ("Today", "day"), ("Previous 6 months", "last_6_months"), ("Previous 12 months", "last_12_months"), ("Year to date", "year_to_date"), ("Yesterday", "yesterday"), ("Last week", "last_week"), ("Last month", "last_month"), ("Previous 3 months", "last_3_months"), ("Current financial year", "current_financial_year"), ("Previous financial year", "previous_financial_year"), ("Custom range", "custom"), ("Calendar year", "calendar_year")): self.report_period.addItem(label, kind)
        self.report_anchor = QDateEdit(QDate.currentDate()); self.report_anchor.setCalendarPopup(True); self.report_anchor.setDisplayFormat("dd MMM yyyy")
        self.report_start = QDateEdit(QDate.currentDate().addMonths(-1)); self.report_start.setCalendarPopup(True); self.report_start.setDisplayFormat("dd MMM yyyy"); self.report_start.setVisible(False)
        self.report_period.currentIndexChanged.connect(lambda _index: self.report_start.setVisible(self.report_period.currentData() == "custom"))
        generate = QPushButton("Generate report", objectName="primary"); generate.clicked.connect(self._generate_report); export_pdf = QPushButton("Export PDF"); export_pdf.clicked.connect(self._export_current_report_pdf)
        controls.addWidget(QLabel("Period")); controls.addWidget(self.report_period); controls.addWidget(QLabel("Start / as of")); controls.addWidget(self.report_start); controls.addWidget(self.report_anchor); controls.addWidget(generate); controls.addWidget(export_pdf); controls.addStretch(); view.addLayout(controls)
        self.report_output = QLabel("Select a period and generate a report."); self.report_output.setWordWrap(True); self.report_output.setObjectName("overviewCard"); view.addWidget(self.report_output); view.addStretch(); return widget

    def _budget_page(self):
        widget, view = self._page("Budgets & Targets", "Budgets compare planned amounts with verified expenses. They never turn missing records into zero spending.")
        form = QHBoxLayout(); self.budget_category = QLineEdit(); self.budget_category.setPlaceholderText("Category, e.g. Rent"); self.budget_amount = QLineEdit(); self.budget_amount.setPlaceholderText("Amount")
        self.budget_start = QDateEdit(QDate.currentDate().addDays(-QDate.currentDate().day() + 1)); self.budget_start.setCalendarPopup(True); self.budget_end = QDateEdit(QDate.currentDate()); self.budget_end.setCalendarPopup(True)
        save = QPushButton("Save budget", objectName="primary"); save.clicked.connect(self._save_budget); deactivate = QPushButton("Deactivate selected"); deactivate.clicked.connect(self._deactivate_budget)
        for item in (QLabel("Category"), self.budget_category, QLabel("Amount"), self.budget_amount, self.budget_start, self.budget_end, save, deactivate): form.addWidget(item)
        view.addLayout(form); self.budget_table = QTableWidget(0, 6); self.budget_table.setHorizontalHeaderLabels(["Category", "Start", "End", "Budget", "Currency", "Active"]); self.budget_table.setSelectionBehavior(QTableWidget.SelectRows); self.budget_table.cellDoubleClicked.connect(self._load_budget); view.addWidget(self.budget_table); view.addStretch(); return widget

    def _navigate(self, label, push=True):
        pages = {"Home": (self.home, "Home"), "Overview": (self.overview, "Business Overview"), "Analytics": (self.analytics, "Analytics"), "Process Invoices": (self.process, "Invoices & Documents"), "Results": (self.results, "Results"), "Review": (self.review, "Review"), "Reports": (self.reports, "Reports & Analytics"), "Budgets": (self.budgets, "Budgets & Targets"), "Settings": (self.settings, "Settings & Data"), "About": (self.about, "About InvoiceFlow"), "Sales": (self.sales, "Sales & Income"), "Purchases": (self.purchases, "Purchases & Expenses"), "Expenses": (self.expenses, "Expenses"), "Money Received": (self.received, "Money Received"), "Money Paid": (self.paid, "Money Paid"), "Customers & Suppliers": (self.parties, "Customers & Suppliers"), "Business Insights": (self.insights, "Business Insights")}
        if label not in pages: return
        if label == "Home": self._navigation.clear(); push=False
        if push and label != self._current_page: self._navigation.append(self._current_page)
        widget, title = pages[label]; self.stack.setCurrentWidget(widget); self.location.setText(title); self._current_page=label; self._refresh()

    def _back(self):
        if self._navigation:
            self._navigate(self._navigation.pop(),False)
        else:
            self._navigate("Home",False)

    def _generate_report(self):
        try:
            kind = self.report_period.currentData(); anchor = self.report_anchor.date().toPython(); period = period_between(self.report_start.date().toPython(), anchor) if kind == "custom" else period_for(kind, anchor); ledger = LedgerStore(DB_PATH); transactions = ledger.list(verified_only=True); ledger.close()
            if not transactions:
                records = self.store.load(); explicit = {r.record_id: r.invoice_type for r in records if r.invoice_type in {"sale", "purchase", "expense", "collection", "payment"}}; transactions = transactions_from_invoices(records, explicit)
            report = build_report(transactions, period, "INR"); self.current_report = report; metrics = "\n".join(f"{metric.name}: {metric.value:,.2f} {metric.currency}" for metric in report.metrics.values() if metric.value is not None); notes = "\n".join(report.data_quality) or "Data quality checks passed for available records."; self.report_output.setText(f"{report.period.label}\n\n{metrics}\n\n{notes}")
        except Exception as exc: self.report_output.setText(f"Unable to generate report: {exc}")

    def _export_current_report_pdf(self):
        if not hasattr(self, "current_report"):
            QMessageBox.information(self, "Generate a report first", "Generate a report before exporting it."); return
        path, _ = QFileDialog.getSaveFileName(self, "Export business report", str(Path.home() / "invoiceflow_report.pdf"), "PDF (*.pdf)")
        if path:
            try: export_report_pdf(self.current_report, path); QMessageBox.information(self, "Export complete", f"Saved report to {path}")
            except Exception as exc: QMessageBox.critical(self, "Export failed", str(exc))

    def _refresh_overview(self):
        try:
            kind = self.overview_period.currentData(); anchor = self.overview_anchor.date().toPython()
            if kind == "custom": period = period_between(self.overview_start.date().toPython(), anchor)
            else: period = period_for(kind, anchor)
            ledger = LedgerStore(DB_PATH); transactions = ledger.list(verified_only=True); ledger.close()
            snapshot = build_analytics(transactions, period, "INR", previous_period(period))
            lines = [f"{period.label} ({period.start.isoformat()} to {period.end.isoformat()})"]
            labels = (("sales", "Sales"), ("purchases", "Purchases"), ("expenses", "Expenses"), ("gross_profit", "Gross profit"), ("net_profit", "Net profit"), ("collections", "Collections received"), ("payments", "Payments made"))
            for key, label in labels:
                metric = snapshot.kpis[key]
                value = "Insufficient data" if metric["value"] is None else f"{metric['value']:,.2f} {snapshot.currency}"
                comparison = ""
                if metric["change"] is not None: comparison = f" ({metric['change']:+.1%} vs previous period)"
                lines.append(f"{label}: {value}{comparison}")
            lines.append(f"Verified transactions: {snapshot.kpis['transaction_count']['value']}")
            if snapshot.data_quality: lines.append("\nData completeness:\n• " + "\n• ".join(snapshot.data_quality))
            self.overview_text.setText("\n".join(lines))
            self.revenue_chart.set_monthly(snapshot.monthly, self._show_source_transactions)
            self.expense_chart.set_categories(snapshot.expense_categories, self._show_source_transactions)
        except Exception as exc:
            self.overview_text.setText(f"Unable to refresh overview: {exc}")

    def _refresh_analytics(self):
        try:
            period=period_for("last_12_months"); ledger=LedgerStore(DB_PATH); snapshot=build_analytics(ledger.list(verified_only=True),period,"INR",previous_period(period)); ledger.close()
            lines=[f"{period.label}: {period.start.isoformat()} to {period.end.isoformat()}"]
            for key,label in (("sales","Revenue"),("purchases","Purchases"),("expenses","Operating expenses"),("collections","Collections"),("payments","Payments"),("gross_profit","Estimated gross profit"),("net_profit","Estimated net profit")):
                metric=snapshot.kpis[key]; value="Insufficient data" if metric["value"] is None else f"{metric['value']:,.2f} {snapshot.currency}"; lines.append(f"{label}: {value}")
            if snapshot.data_quality: lines.append("\nData completeness:\n• " + "\n• ".join(snapshot.data_quality))
            self.analytics_text.setText("\n".join(lines)); self.analytics_revenue_chart.set_monthly(snapshot.monthly,self._show_source_transactions); self.analytics_expense_chart.set_categories(snapshot.expense_categories,self._show_source_transactions)
        except Exception as exc: self.analytics_text.setText(f"Unable to refresh analytics: {exc}")

    def _show_source_transactions(self, source_ids):
        identifiers = ", ".join(str(value) for value in source_ids if value) or "No source IDs available"
        QMessageBox.information(self, "Source transactions", f"The selected chart value is supported by these verified source records:\n{identifiers}")

    def _refresh_budgets(self):
        ledger = LedgerStore(DB_PATH); rows = ledger.list_budgets(); ledger.close(); self.budget_table.setRowCount(len(rows))
        for row, item in enumerate(rows):
            values = [item["category"], item["period_start"], item["period_end"], item["amount"], item["currency"], "Yes" if item.get("active", 1) else "No"]
            for column, value in enumerate(values):
                cell = QTableWidgetItem(str(value));
                if column == 0: cell.setData(32, item["budget_id"])
                self.budget_table.setItem(row, column, cell)
        self.budget_table.resizeColumnsToContents()

    def _save_budget(self):
        try:
            category = self.budget_category.text().strip(); amount = self.budget_amount.text().strip(); start = self.budget_start.date().toPython().isoformat(); end = self.budget_end.date().toPython().isoformat()
            if not category or not amount: raise ValueError("Enter a budget category and amount")
            ledger = LedgerStore(DB_PATH); selected = self.budget_table.selectionModel().selectedRows();
            if selected:
                budget_id = self.budget_table.item(selected[0].row(), 0).data(32); ledger.update_budget(int(budget_id), start, end, category, amount, "INR")
            else: ledger.add_budget(1, start, end, category, amount, "INR")
            ledger.close(); self._refresh_budgets()
        except Exception as exc: QMessageBox.warning(self, "Budget not saved", str(exc))

    def _load_budget(self, row, _column):
        self.budget_category.setText(self.budget_table.item(row, 0).text()); self.budget_amount.setText(self.budget_table.item(row, 3).text()); self.budget_start.setDate(QDate.fromString(self.budget_table.item(row, 1).text(), "yyyy-MM-dd")); self.budget_end.setDate(QDate.fromString(self.budget_table.item(row, 2).text(), "yyyy-MM-dd"))

    def _deactivate_budget(self):
        selected = self.budget_table.selectionModel().selectedRows()
        if not selected: return
        budget_id = self.budget_table.item(selected[0].row(), 0).data(32); ledger = LedgerStore(DB_PATH); ledger.set_budget_active(int(budget_id), False); ledger.close(); self._refresh_budgets()

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
        if hasattr(self, "overview_text"):
            self.overview_text.setText(summary + "\n\nOpen Business Overview to inspect verified financial KPIs and charts.")
            self._refresh_overview()
        if hasattr(self, "budget_table"): self._refresh_budgets()
        if hasattr(self, "table"): self._refresh_table()
        for key in ("sales", "purchases", "expenses", "received", "paid"):
            if hasattr(self, f"{key}_table"): self._refresh_transaction_page(key)
        if hasattr(self, "party_table"): self._refresh_parties_and_insights()
        if hasattr(self, "analytics_text"): self._refresh_analytics()
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
