from __future__ import annotations

from pathlib import Path
from decimal import Decimal
import json
import sqlite3
from datetime import datetime

from PySide6.QtCore import QDate, QThread, Qt
from PySide6.QtGui import QCloseEvent, QDesktopServices, QPixmap
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDateEdit, QFileDialog, QFrame, QFormLayout, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMessageBox, QPushButton, QProgressBar, QScrollArea, QSizePolicy, QStackedWidget, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget, QInputDialog, QDialog, QTabWidget, QTextEdit)

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
from .import_dialog import ImportDialog
from .components import card, empty_state, section_title, set_table_defaults
from .branding import application_icon, logo_pixmap
from .theme import stylesheet
from src.aging import build_aging
from src.config import APP_VERSION


class MainWindow(QMainWindow):
    """Native desktop shell with a card-based home screen and functional pages."""

    def __init__(self):
        super().__init__()
        self.setWindowIcon(application_icon())
        self.setWindowTitle(f"{APP_NAME} — PDF invoices → structured data")
        self.setMinimumSize(900, 680)
        self.records = []
        self.store = HistoryStore(DB_PATH)
        self.thread = None
        self.worker = None
        self._navigation=[]
        self._current_page="Home"
        self._build()
        self._refresh()

    def _build(self):
        self.theme_preference = self._setting("theme", "light")
        self.setStyleSheet(stylesheet(self.theme_preference))
        root = QWidget()
        shell = QHBoxLayout(root)
        shell.setContentsMargins(0, 0, 0, 0)
        shell.setSpacing(0)
        self.sidebar = self._sidebar()
        shell.addWidget(self.sidebar)
        content = QWidget(objectName="contentShell")
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        header = QHBoxLayout()
        header_widget = QWidget(objectName="appHeader")
        header_widget.setLayout(header)
        header.setContentsMargins(24, 14, 24, 14)
        self.location = QLabel("Overview", objectName="breadcrumb")
        header.addWidget(self.location)
        header.addStretch()
        self.header_status = QLabel("Local data · saved on this computer", objectName="breadcrumb")
        header.addWidget(self.header_status)
        content_layout.addWidget(header_widget)
        self.stack = QStackedWidget()
        self.stack.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        content_layout.addWidget(self.stack, 1)
        shell.addWidget(content, 1)
        self.setCentralWidget(root)

        self.home = self._home()
        self.process = self._process()
        self.results = self._results()
        self.review = self._review()
        self.reports = self._reports()
        self.budgets = self._budget_page()
        self.settings = self._settings_page()
        self.about = self._simple("About InvoiceFlow", f"InvoiceFlow {APP_VERSION}\nPDF invoices → structured data\n\nDeterministic local invoice processing with transparent review flags.")
        self.overview = self._overview()
        self.analytics = self._analytics_page()
        self.sales = self._transaction_page("Sales & Income", {"sale", "sales_return", "collection"}, "sales")
        self.purchases = self._transaction_page("Purchases & Expenses", {"purchase", "purchase_return", "expense", "payment", "supplier_payment"}, "purchases")
        self.expenses = self._transaction_page("Expenses", {"expense"}, "expenses")
        self.received = self._transaction_page("Money Received", {"collection"}, "received")
        self.paid = self._transaction_page("Money Paid", {"payment", "supplier_payment"}, "paid")
        self.transactions = self._transaction_page("Transactions", {"sale", "sales_return", "purchase", "purchase_return", "expense", "collection", "payment", "supplier_payment", "adjustment"}, "transactions")
        self.parties = self._party_page()
        self.receivables = self._aging_page("receivable")
        self.payables = self._aging_page("payable")
        self.import_history = self._import_history_page()
        self.insights = self._insights_page()
        self.import_page = self._import_page()
        self.reconciliation = self._reconciliation_page()
        for widget in (self.home, self.process, self.results, self.review, self.reports, self.budgets, self.settings, self.about, self.overview, self.analytics, self.sales, self.purchases, self.expenses, self.received, self.paid, self.transactions, self.parties, self.receivables, self.payables, self.import_history, self.insights, self.import_page, self.reconciliation):
            self.stack.addWidget(widget)
        # Compatibility handles retained for existing integrations and tests.
        self.nav = [self._compat_nav_button("Overview", "Overview"), self._compat_nav_button("Invoice Processing", "Process Invoices")]
        self._navigate("Home",False)
        self.overview_period.currentIndexChanged.connect(self._refresh_financial_views)
        self.overview_anchor.dateChanged.connect(self._refresh_financial_views)
        self.overview_start.dateChanged.connect(self._refresh_financial_views)
        self._maybe_onboard()
        self._apply_chart_theme(self.theme_preference)

    def _apply_chart_theme(self, preference: str) -> None:
        for chart in self.findChildren(FinancialChart):
            chart.apply_theme("dark" if preference == "dark" else "light")

    def _setting(self, key: str, default: str = "") -> str:
        ledger = LedgerStore(DB_PATH)
        try:
            return ledger.get_setting(key, default)
        finally:
            ledger.close()

    def _compat_nav_button(self, label, page):
        button = QPushButton(label, self)
        button.clicked.connect(lambda checked=False, target=page: self._navigate(target))
        button.hide()
        return button

    def _sidebar(self):
        sidebar = QFrame(objectName="sidebar")
        self.sidebar_collapsed = self._setting("sidebar_collapsed", "0") == "1"
        sidebar.setMinimumWidth(76 if self.sidebar_collapsed else 196)
        sidebar.setMaximumWidth(76 if self.sidebar_collapsed else 280)
        sidebar.setFixedWidth(76 if self.sidebar_collapsed else 224)
        outer = QVBoxLayout(sidebar)
        outer.setContentsMargins(16, 20, 16, 16)
        outer.setSpacing(8)
        brand_row = QHBoxLayout()
        logo = QLabel(objectName="brandLogo")
        logo.setPixmap(logo_pixmap(42))
        logo.setFixedSize(42, 42)
        brand_row.addWidget(logo)
        self.sidebar_brand = QLabel("InvoiceFlow", objectName="brand")
        brand_row.addWidget(self.sidebar_brand)
        self.sidebar_toggle = QPushButton("»" if not self.sidebar_collapsed else "«", objectName="sidebarToggle")
        self.sidebar_toggle.setToolTip("Collapse sidebar" if not self.sidebar_collapsed else "Expand sidebar")
        self.sidebar_toggle.clicked.connect(self._toggle_sidebar)
        brand_row.addWidget(self.sidebar_toggle)
        brand_row.addStretch()
        outer.addLayout(brand_row)
        subtitle = QLabel("Financial workspace")
        subtitle.setObjectName("breadcrumb")
        self.sidebar_subtitle = subtitle
        outer.addWidget(subtitle)
        navigation_scroll = QScrollArea()
        navigation_scroll.setWidgetResizable(True)
        navigation_scroll.setFrameShape(QFrame.Shape.NoFrame)
        navigation_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        navigation_content = QWidget()
        layout = QVBoxLayout(navigation_content)
        layout.setContentsMargins(0, 8, 4, 8)
        layout.setSpacing(3)
        navigation_scroll.setWidget(navigation_content)
        outer.addWidget(navigation_scroll, 1)
        self.sidebar_buttons = {}
        sections = (
            ("WORKSPACE", (("Overview", "Overview"), ("Analytics", "Analytics"))),
            ("FINANCIALS", (("Sales & Income", "Sales"), ("Purchases", "Purchases"), ("Expenses", "Expenses"), ("Money Received", "Money Received"), ("Money Paid", "Money Paid"), ("Receivables", "Receivables"), ("Payables", "Payables"), ("Transactions", "Transactions"))),
            ("MANAGEMENT", (("Customers", "Customers & Suppliers"), ("Suppliers", "Customers & Suppliers"), ("Budgets & Targets", "Budgets"), ("Business Insights", "Business Insights"))),
            ("DOCUMENTS", (("Upload Documents", "Process Invoices"), ("Invoice Processing", "Results"), ("Import Centre", "Import Data"))),
            ("REPORTING", (("Reports", "Reports"),)),
            ("SYSTEM", (("Settings", "Settings"), ("Data Management", "Settings"), ("Import History", "Import History"))),
        )
        for heading, items in sections:
            label = QLabel(heading)
            label.setObjectName("sidebarSection")
            label.setProperty("sidebarHeading", True)
            if self.sidebar_collapsed:
                label.hide()
            layout.addWidget(label)
            for text, page in items:
                button = QPushButton(text, objectName="navButton")
                button.setCheckable(True)
                button.setToolTip(text)
                if self.sidebar_collapsed:
                    button.setText("")
                button.clicked.connect(lambda checked=False, target=page: self._navigate(target))
                layout.addWidget(button)
                self.sidebar_buttons.setdefault(page, []).append(button)
        layout.addStretch()
        footer = QLabel(f"InvoiceFlow {APP_VERSION}\nLocal-first financial records")
        footer.setObjectName("breadcrumb")
        self.sidebar_footer = footer
        outer.addWidget(footer)
        if self.sidebar_collapsed:
            self.sidebar_brand.hide()
            self.sidebar_subtitle.hide()
            self.sidebar_footer.hide()
        return sidebar

    def _toggle_sidebar(self):
        self.sidebar_collapsed = not self.sidebar_collapsed
        self.sidebar.setFixedWidth(76 if self.sidebar_collapsed else 224)
        self.sidebar.setMinimumWidth(76 if self.sidebar_collapsed else 196)
        self.sidebar.setMaximumWidth(76 if self.sidebar_collapsed else 280)
        self.sidebar_toggle.setText("«" if self.sidebar_collapsed else "»")
        self.sidebar_toggle.setToolTip("Expand sidebar" if self.sidebar_collapsed else "Collapse sidebar")
        self.sidebar_brand.setVisible(not self.sidebar_collapsed)
        self.sidebar_subtitle.setVisible(not self.sidebar_collapsed)
        self.sidebar_footer.setVisible(not self.sidebar_collapsed)
        for button_group in self.sidebar_buttons.values():
            for button in button_group:
                button.setText("" if self.sidebar_collapsed else button.toolTip())
        for heading in self.sidebar.findChildren(QLabel):
            if heading.property("sidebarHeading"):
                heading.setVisible(not self.sidebar_collapsed)
        ledger = LedgerStore(DB_PATH)
        try:
            ledger.set_setting("sidebar_collapsed", "1" if self.sidebar_collapsed else "0")
        finally:
            ledger.close()

    def _page(self, title, explanation=""):
        scroll = QScrollArea(objectName="pageScroll")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        widget = QWidget(objectName="pageContent")
        scroll.setWidget(widget)
        view = QVBoxLayout(widget); view.setContentsMargins(28, 22, 28, 28); view.setSpacing(16)
        header=QHBoxLayout(); back=QPushButton("← Back",objectName="backButton"); back.clicked.connect(self._back); header.addWidget(back); header.addWidget(QLabel(title, objectName="pageTitle")); header.addStretch(); view.addLayout(header)
        if title == "Welcome to InvoiceFlow":
            back.hide()
        if explanation:
            note = QLabel(explanation, objectName="pageExplanation"); note.setWordWrap(True); view.addWidget(note)
        return scroll, view

    def _simple(self, title, text):
        widget, view = self._page(title, text); view.addStretch(); return widget

    def _card(self, title, description, page):
        card = QPushButton(f"{title}\n{description}", objectName="featureCard")
        card.setMinimumHeight(128); card.setToolTip(description)
        card.clicked.connect(lambda checked=False, target=page: self._navigate(target))
        return card

    def _home(self):
        widget, view = self._page("Dashboard", "A clear view of verified financial activity, cash movement and the decisions that need attention.")
        hero = QFrame(objectName="heroCard")
        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(24, 20, 24, 20)
        intro = QVBoxLayout()
        self.welcome_title = QLabel("Good to see you", objectName="heroTitle")
        intro.addWidget(self.welcome_title)
        self.stats = QLabel("Your verified business snapshot is loading…", objectName="heroSubtitle")
        self.stats.setWordWrap(True)
        intro.addWidget(self.stats)
        hero_layout.addLayout(intro, 1)
        hero_actions = QVBoxLayout()
        self.home_date = QLabel(objectName="heroDate")
        self.home_date.setAlignment(Qt.AlignmentFlag.AlignRight)
        hero_actions.addWidget(self.home_date)
        period_button = QPushButton("View analytics", objectName="heroAction")
        period_button.clicked.connect(lambda: self._navigate("Analytics"))
        hero_actions.addWidget(period_button, 0, Qt.AlignmentFlag.AlignRight)
        hero_layout.addLayout(hero_actions)
        view.addWidget(hero)

        toolbar = QHBoxLayout()
        toolbar.addWidget(section_title("Financial snapshot"))
        toolbar.addStretch()
        add_button = QPushButton("+ Add transaction", objectName="primary")
        add_button.clicked.connect(lambda: self._quick_action("adjustment"))
        toolbar.addWidget(add_button)
        upload_button = QPushButton("Upload documents")
        upload_button.clicked.connect(lambda: self._quick_action("upload"))
        toolbar.addWidget(upload_button)
        view.addLayout(toolbar)

        kpis = QGridLayout(); kpis.setSpacing(14); self.home_kpis = {}
        for index, (key, label, hint, accent) in enumerate((
            ("sales", "Revenue", "Verified sales less returns", "teal"),
            ("expenses", "Expenses", "Verified operating expenses", "amber"),
            ("gross_profit", "Estimated gross profit", "Revenue less purchases", "navy"),
            ("collections", "Collections", "Explicit cash received", "sage"),
            ("receivables", "Receivables", "Unallocated sales balance", "blue"),
            ("payables", "Payables", "Unallocated purchase balance", "purple"),
        )):
            frame = card(object_name="metricCard")
            frame.setProperty("accent", accent)
            frame_layout = QVBoxLayout(frame); frame_layout.setContentsMargins(18, 15, 18, 15); frame_layout.setSpacing(4)
            top = QHBoxLayout()
            label_widget = QLabel(label, objectName="metricLabel")
            top.addWidget(label_widget); top.addStretch()
            badge = QLabel("VERIFIED", objectName="metricBadge"); top.addWidget(badge)
            frame_layout.addLayout(top)
            value = QLabel("—", objectName="metricValue"); value.setToolTip(hint); frame_layout.addWidget(value)
            frame_layout.addWidget(QLabel(hint, objectName="metricHint"))
            self.home_kpis[key] = value
            kpis.addWidget(frame, index // 3, index % 3)
        view.addLayout(kpis)

        view.addWidget(section_title("Business pulse"))
        charts = QGridLayout(); charts.setSpacing(14)
        self.home_revenue_chart = FinancialChart("Revenue trend")
        self.home_revenue_chart.setObjectName("chartCard")
        self.home_expense_chart = FinancialChart("Expense composition")
        self.home_expense_chart.setObjectName("chartCard")
        charts.addWidget(self.home_revenue_chart, 0, 0, 1, 2)
        charts.addWidget(self.home_expense_chart, 1, 0)
        budget_card = card(object_name="insightCard")
        budget_layout = QVBoxLayout(budget_card); budget_layout.setContentsMargins(18, 16, 18, 16)
        budget_layout.addWidget(QLabel("Budget watch", objectName="cardTitle"))
        self.home_budget_text = QLabel("Budget utilization appears here when active budgets overlap the selected period.", objectName="cardBody")
        self.home_budget_text.setWordWrap(True); budget_layout.addWidget(self.home_budget_text)
        budget_button = QPushButton("Manage budgets")
        budget_button.clicked.connect(lambda: self._navigate("Budgets"))
        budget_layout.addWidget(budget_button, 0, Qt.AlignmentFlag.AlignLeft)
        charts.addWidget(budget_card, 1, 1)
        view.addLayout(charts)

        view.addWidget(section_title("Recent activity"))
        activity_frame = card(object_name="activityCard")
        activity_layout = QVBoxLayout(activity_frame); activity_layout.setContentsMargins(16, 12, 16, 12)
        activity_header = QHBoxLayout()
        activity_header.addWidget(QLabel("Latest verified records", objectName="cardTitle")); activity_header.addStretch()
        all_transactions = QPushButton("View all")
        all_transactions.clicked.connect(lambda: self._navigate("Transactions"))
        activity_header.addWidget(all_transactions); activity_layout.addLayout(activity_header)
        self.home_activity = QTableWidget(0, 4)
        self.home_activity.setHorizontalHeaderLabels(["Date", "Activity", "Counterparty", "Amount"])
        set_table_defaults(self.home_activity)
        activity_layout.addWidget(self.home_activity)
        view.addWidget(activity_frame)
        self.home_cards = []
        return widget

    def _quick_action(self, kind):
        if kind == "upload": self._navigate("Process Invoices")
        else: self._open_transaction(kind)

    def _overview(self):
        widget, view = self._page("Business Overview", "Verified transactions only. If a figure is unavailable, InvoiceFlow explains which records are missing.")
        controls = QHBoxLayout(); self.overview_period = QComboBox()
        for label, kind in (("Today", "day"), ("Yesterday", "yesterday"), ("This week", "week"), ("Last week", "last_week"), ("This month", "month"), ("Last month", "last_month"), ("Previous 3 months", "last_3_months"), ("Previous 6 months", "last_6_months"), ("Previous 12 months", "last_12_months"), ("Year to date", "year_to_date"), ("Current financial year", "current_financial_year"), ("Custom range", "custom")): self.overview_period.addItem(label, kind)
        self.overview_anchor = QDateEdit(QDate.currentDate()); self.overview_anchor.setCalendarPopup(True); self.overview_anchor.setDisplayFormat("dd MMM yyyy")
        self.overview_start = QDateEdit(QDate.currentDate().addMonths(-1)); self.overview_start.setCalendarPopup(True); self.overview_start.setDisplayFormat("dd MMM yyyy"); self.overview_start.setVisible(False)
        refresh = QPushButton("Refresh overview", objectName="primary"); refresh.clicked.connect(self._refresh_overview)
        self.overview_period.currentIndexChanged.connect(lambda _index: self.overview_start.setVisible(self.overview_period.currentData() == "custom"))
        controls.addWidget(QLabel("Period")); controls.addWidget(self.overview_period); controls.addWidget(QLabel("As of")); controls.addWidget(self.overview_anchor); controls.addWidget(self.overview_start); controls.addWidget(refresh); controls.addStretch(); view.addLayout(controls)
        self.overview_text = QLabel(objectName="overviewCard"); self.overview_text.setWordWrap(True); view.addWidget(self.overview_text)
        charts = QGridLayout(); self.revenue_chart = FinancialChart("Revenue vs expenses"); self.expense_chart = FinancialChart("Expense categories"); charts.addWidget(self.revenue_chart, 0, 0); charts.addWidget(self.expense_chart, 0, 1); view.addLayout(charts); view.addStretch(); return widget

    def _analytics_page(self):
        widget, view = self._page("Analytics", "Explore verified financial activity using the same selected period across every KPI, chart, table and insight.")
        controls = QHBoxLayout()
        self.analytics_period = QComboBox()
        for label, kind in (("Today", "day"), ("Yesterday", "yesterday"), ("This week", "week"), ("Last week", "last_week"), ("This month", "month"), ("Last month", "last_month"), ("Last 3 months", "last_3_months"), ("Last 6 months", "last_6_months"), ("Last 12 months", "last_12_months"), ("Year to date", "year_to_date"), ("Current financial year", "current_financial_year"), ("Previous financial year", "previous_financial_year"), ("Custom range", "custom")):
            self.analytics_period.addItem(label, kind)
        self.analytics_anchor = QDateEdit(QDate.currentDate())
        self.analytics_anchor.setCalendarPopup(True)
        self.analytics_anchor.setDisplayFormat("dd MMM yyyy")
        self.analytics_start = QDateEdit(QDate.currentDate().addMonths(-1))
        self.analytics_start.setCalendarPopup(True)
        self.analytics_start.setDisplayFormat("dd MMM yyyy")
        self.analytics_start.setVisible(False)
        self.analytics_period.currentIndexChanged.connect(lambda _: self.analytics_start.setVisible(self.analytics_period.currentData() == "custom"))
        self.analytics_period.currentIndexChanged.connect(self._refresh_analytics)
        self.analytics_anchor.dateChanged.connect(self._refresh_analytics)
        self.analytics_start.dateChanged.connect(self._refresh_analytics)
        refresh = QPushButton("Refresh", objectName="primary")
        refresh.clicked.connect(self._refresh_analytics)
        controls.addWidget(QLabel("Period"))
        controls.addWidget(self.analytics_period)
        controls.addWidget(QLabel("As of"))
        controls.addWidget(self.analytics_anchor)
        controls.addWidget(self.analytics_start)
        controls.addWidget(refresh)
        controls.addStretch()
        view.addLayout(controls)
        self.analytics_period_label = QLabel("Loading analytics…", objectName="pageExplanation")
        view.addWidget(self.analytics_period_label)
        self.analytics_text = self.analytics_period_label
        view.addWidget(section_title("Financial snapshot"))
        self.analytics_kpi_values = {}
        self.analytics_kpi_frames = []
        kpi_grid = QGridLayout()
        kpi_grid.setSpacing(12)
        self.analytics_kpi_grid = kpi_grid
        for index, (key, label, hint) in enumerate((
            ("sales", "Revenue", "Verified sales less sales returns"),
            ("purchases", "Purchases", "Verified purchases less purchase returns"),
            ("expenses", "Operating expenses", "Verified operating expenses only"),
            ("gross_profit", "Estimated gross profit", "Revenue less purchases; inventory is not valued"),
            ("collections", "Collections", "Explicit customer collections"),
            ("payments", "Payments", "Explicit supplier and operating payments"),
            ("receivables", "Outstanding receivables", "Unallocated verified sales"),
            ("payables", "Outstanding payables", "Unallocated verified purchases"),
        )):
            frame = card(object_name="kpiCard")
            box = QVBoxLayout(frame)
            box.addWidget(QLabel(label, objectName="kpiLabel"))
            value = QLabel("—", objectName="kpiValue")
            value.setToolTip(hint)
            box.addWidget(value)
            box.addWidget(QLabel(hint, objectName="kpiHint"))
            self.analytics_kpi_values[key] = value
            self.analytics_kpi_frames.append(frame)
            kpi_grid.addWidget(frame, index // 4, index % 4)
        view.addLayout(kpi_grid)
        self.analytics_quality = QLabel(objectName="pageExplanation")
        self.analytics_quality.setWordWrap(True)
        view.addWidget(self.analytics_quality)
        charts = QGridLayout()
        charts.setSpacing(12)
        self.analytics_revenue_chart = FinancialChart("Revenue, purchases and operating expenses")
        self.analytics_expense_chart = FinancialChart("Operating expense categories")
        self.analytics_cash_chart = FinancialChart("Collections and payments")
        self.analytics_trend_chart = FinancialChart("Revenue trend")
        self.analytics_budget_chart = FinancialChart("Budget utilization")
        charts.addWidget(self.analytics_revenue_chart, 0, 0)
        charts.addWidget(self.analytics_expense_chart, 0, 1)
        charts.addWidget(self.analytics_cash_chart, 1, 0)
        charts.addWidget(self.analytics_trend_chart, 1, 1)
        charts.addWidget(self.analytics_budget_chart, 2, 0, 1, 2)
        view.addLayout(charts)
        self.analytics_budget_summary = QLabel(objectName="pageExplanation")
        self.analytics_budget_summary.setWordWrap(True)
        view.addWidget(self.analytics_budget_summary)
        lower = QGridLayout()
        lower.setSpacing(12)
        self.analytics_customers = QTableWidget(0, 2)
        self.analytics_customers.setHorizontalHeaderLabels(["Top customers", "Revenue"])
        set_table_defaults(self.analytics_customers)
        self.analytics_suppliers = QTableWidget(0, 2)
        self.analytics_suppliers.setHorizontalHeaderLabels(["Top suppliers", "Purchases"])
        set_table_defaults(self.analytics_suppliers)
        self.analytics_transactions = QTableWidget(0, 4)
        self.analytics_transactions.setHorizontalHeaderLabels(["Date", "Type", "Party", "Amount"])
        set_table_defaults(self.analytics_transactions)
        self.analytics_insights = QLabel("No financial insights for this period.")
        self.analytics_insights.setObjectName("emptyState")
        self.analytics_insights.setWordWrap(True)
        lower.addWidget(self.analytics_customers, 0, 0)
        lower.addWidget(self.analytics_suppliers, 0, 1)
        lower.addWidget(self.analytics_transactions, 1, 0, 1, 2)
        view.addWidget(section_title("Recent transactions and performance"))
        view.addLayout(lower)
        view.addWidget(section_title("Financial insights and data quality"))
        view.addWidget(self.analytics_insights)
        view.addStretch()
        return widget

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "analytics_kpi_grid"):
            columns = 4 if self.width() >= 1150 else 2
            for index, frame in enumerate(self.analytics_kpi_frames):
                self.analytics_kpi_grid.addWidget(frame, index // columns, index % columns)

    def _process(self):
        widget, view = self._page("Invoice workspace", "Turn source documents into reviewable records without mixing batch results into your business ledger.")
        upload_card = QFrame(objectName="uploadCard")
        upload_layout = QVBoxLayout(upload_card); upload_layout.setContentsMargins(30, 28, 30, 28); upload_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        upload_layout.addWidget(QLabel("Upload invoices and receipts", objectName="uploadTitle"), 0, Qt.AlignmentFlag.AlignCenter)
        self.selected = QLabel("Drop PDF or ZIP files here, or browse from your computer.", objectName="uploadHint")
        self.selected.setAlignment(Qt.AlignmentFlag.AlignCenter); upload_layout.addWidget(self.selected)
        row = QHBoxLayout(); row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        choose = QPushButton("Browse files", objectName="primary"); choose.clicked.connect(self._choose)
        clear = QPushButton("Clear selection"); clear.clicked.connect(lambda: self._set_files([]))
        row.addWidget(choose); row.addWidget(clear); upload_layout.addLayout(row)
        upload_layout.addWidget(QLabel("Supported: PDF and ZIP · Processing stays local · Original files are never silently changed.", objectName="uploadMeta"), 0, Qt.AlignmentFlag.AlignCenter)
        view.addWidget(upload_card)
        self.progress = QProgressBar(); self.current = QLabel(); view.addWidget(self.progress); view.addWidget(self.current)
        controls = QHBoxLayout()
        self.start = QPushButton("Start processing", objectName="primary"); self.start.clicked.connect(self._start)
        self.cancel = QPushButton("Cancel"); self.cancel.setEnabled(False); self.cancel.clicked.connect(self._cancel)
        controls.addWidget(self.start); controls.addWidget(self.cancel); controls.addStretch(); view.addLayout(controls)
        view.addWidget(section_title("What happens next"))
        steps = QHBoxLayout()
        for number, title, body in (("01", "Extract", "Read document fields and line items"), ("02", "Review", "Inspect confidence and correct fields"), ("03", "Approve", "Explicitly verify before ledger entry")):
            frame = card(object_name="stepCard"); box = QVBoxLayout(frame); box.addWidget(QLabel(number, objectName="stepNumber")); box.addWidget(QLabel(title, objectName="cardTitle")); text = QLabel(body, objectName="cardBody"); text.setWordWrap(True); box.addWidget(text); steps.addWidget(frame)
        view.addLayout(steps); view.addStretch(); self.files = []; return widget

    def _import_page(self):
        widget, view = self._page("Import centre", "Bring operational data into InvoiceFlow independently. Every import is previewed, validated, deduplicated and recorded.")
        grid = QGridLayout(); grid.setSpacing(14)
        for index, (title, body, kind) in enumerate((
            ("Sales", "Import invoices and revenue records", "sales"),
            ("Purchases", "Import supplier invoices and costs", "purchases"),
            ("Expenses", "Import operating expenses without an invoice", "expenses"),
            ("Collections", "Import money received from customers", "collections"),
            ("Payments", "Import supplier and operating payments", "supplier_payments"),
            ("Returns & adjustments", "Import corrections with provenance", "sales_returns"),
        )):
            frame = QFrame(objectName="importCard"); box = QVBoxLayout(frame); box.setContentsMargins(18, 16, 18, 16)
            box.addWidget(QLabel(title, objectName="cardTitle")); description = QLabel(body, objectName="cardBody"); description.setWordWrap(True); box.addWidget(description)
            action = QPushButton("Choose template / file", objectName="primary" if index == 0 else "")
            action.clicked.connect(self._open_import); box.addWidget(action, 0, Qt.AlignmentFlag.AlignLeft)
            grid.addWidget(frame, index // 3, index % 3)
        view.addLayout(grid)
        note = QLabel("Customer and supplier records use the same safe preview flow. Re-importing an identical file remains idempotent.", objectName="emptyState"); note.setWordWrap(True); view.addWidget(note); view.addStretch(); return widget

    def _open_import(self):
        ledger = LedgerStore(DB_PATH)
        try:
            dialog = ImportDialog(ledger, self)
            result = dialog.exec()
        finally:
            ledger.close()
        if result:
            self._refresh()
            for key in ("sales", "purchases", "expenses", "received", "paid"):
                self._refresh_transaction_page(key)

    def _reconciliation_page(self):
        widget, view = self._page("Payment Reconciliation", "Payments affect an invoice balance only after you allocate them explicitly. Unallocated amounts remain advances or unapplied payments.")
        view.addWidget(QLabel("Select one reviewed invoice and one matching reviewed payment, then enter the amount to allocate."))
        row = QHBoxLayout()
        self.recon_invoices = QTableWidget(0, 5); self.recon_invoices.setHorizontalHeaderLabels(["Date", "Invoice", "Customer / supplier", "Amount", "Balance"]); self.recon_invoices.setSelectionBehavior(QTableWidget.SelectRows); self.recon_invoices.setSelectionMode(QTableWidget.SingleSelection)
        self.recon_payments = QTableWidget(0, 5); self.recon_payments.setHorizontalHeaderLabels(["Date", "Type", "Customer / supplier", "Amount", "Unallocated"]); self.recon_payments.setSelectionBehavior(QTableWidget.SelectRows); self.recon_payments.setSelectionMode(QTableWidget.SingleSelection)
        row.addWidget(self.recon_invoices); row.addWidget(self.recon_payments); view.addLayout(row, 1)
        controls = QHBoxLayout(); self.recon_amount = QLineEdit(); self.recon_amount.setPlaceholderText("Amount to allocate")
        allocate = QPushButton("Allocate payment", objectName="primary"); allocate.clicked.connect(self._allocate_selected)
        controls.addWidget(self.recon_amount); controls.addWidget(allocate); controls.addStretch(); view.addLayout(controls)
        view.addWidget(QLabel("Allocation history"))
        self.recon_history = QTableWidget(0, 6); self.recon_history.setHorizontalHeaderLabels(["ID", "Date", "Party", "Invoice reference", "Amount", "Status"]); self.recon_history.setSelectionBehavior(QTableWidget.SelectRows); view.addWidget(self.recon_history, 1)
        reverse = QPushButton("Reverse selected allocation"); reverse.clicked.connect(self._reverse_selected_allocation); view.addWidget(reverse)
        return widget

    def _refresh_reconciliation(self):
        if not hasattr(self, "recon_invoices"): return
        ledger = LedgerStore(DB_PATH)
        try:
            transactions = ledger.list(verified_only=True)
            invoices = [tx for tx in transactions if tx.transaction_type in {"sale", "purchase"} and ledger.allocation_summary(tx.transaction_id)["remaining"] > 0]
            payments = [tx for tx in transactions if tx.transaction_type in {"collection", "supplier_payment"} and ledger.allocation_summary(tx.transaction_id)["remaining"] > 0]
            self.recon_invoices.setRowCount(len(invoices))
            for row, tx in enumerate(invoices):
                balance = ledger.allocation_summary(tx.transaction_id)["remaining"]
                vals = (tx.transaction_date, tx.reference_number or "—", tx.counterparty, tx.amount, balance)
                for col, val in enumerate(vals):
                    cell = QTableWidgetItem(str(val)); cell.setData(Qt.ItemDataRole.UserRole, tx.transaction_id); self.recon_invoices.setItem(row, col, cell)
            self.recon_payments.setRowCount(len(payments))
            for row, tx in enumerate(payments):
                remaining = ledger.allocation_summary(tx.transaction_id)["remaining"]
                vals = (tx.transaction_date, tx.transaction_type, tx.counterparty, tx.amount, remaining)
                for col, val in enumerate(vals):
                    cell = QTableWidgetItem(str(val)); cell.setData(Qt.ItemDataRole.UserRole, tx.transaction_id); self.recon_payments.setItem(row, col, cell)
            allocations = [a for a in ledger.list_allocations() if a["status"] == "ACTIVE"]
            self.recon_history.setRowCount(len(allocations))
            for row, a in enumerate(allocations):
                vals = (a["allocation_id"], a["payment_date"], a["counterparty"], a["invoice_reference"], a["amount"], a["status"])
                for col, val in enumerate(vals):
                    cell = QTableWidgetItem(str(val)); cell.setData(Qt.ItemDataRole.UserRole, a["allocation_id"]); self.recon_history.setItem(row, col, cell)
        finally: ledger.close()

    def _allocate_selected(self):
        inv_row = self.recon_invoices.currentRow(); pay_row = self.recon_payments.currentRow()
        if inv_row < 0 or pay_row < 0:
            QMessageBox.information(self, "Select records", "Select an invoice and a payment to allocate."); return
        try:
            invoice_id = int(self.recon_invoices.item(inv_row, 0).data(Qt.ItemDataRole.UserRole)); payment_id = int(self.recon_payments.item(pay_row, 0).data(Qt.ItemDataRole.UserRole))
            ledger = LedgerStore(DB_PATH)
            try: ledger.allocate_payment(payment_id, invoice_id, self.recon_amount.text().strip())
            finally: ledger.close()
            self.recon_amount.clear(); self._refresh(); self._refresh_reconciliation()
        except Exception as exc: QMessageBox.warning(self, "Allocation not saved", str(exc))

    def _reverse_selected_allocation(self):
        row = self.recon_history.currentRow()
        if row < 0: return
        reason, accepted = QInputDialog.getText(self, "Reverse allocation", "Reason for reversing this allocation:")
        if not accepted: return
        try:
            allocation_id = int(self.recon_history.item(row, 0).data(Qt.ItemDataRole.UserRole)); ledger = LedgerStore(DB_PATH)
            try: ledger.reverse_allocation(allocation_id, reason)
            finally: ledger.close()
            self._refresh(); self._refresh_reconciliation()
        except Exception as exc: QMessageBox.warning(self, "Could not reverse allocation", str(exc))

    def _results(self):
        widget, view = self._page("Results", "Search, inspect and export the records produced by InvoiceFlow.")
        row = QHBoxLayout(); self.search = QLineEdit(); self.search.setPlaceholderText("Search invoice number, vendor or filename"); self.search.textChanged.connect(self._refresh_table); row.addWidget(self.search)
        for label, kind in (("Export Excel", "xlsx"), ("Export CSV", "csv"), ("Export JSON", "json")):
            export = QPushButton(label); export.clicked.connect(lambda checked=False, selected_kind=kind: self._export(selected_kind)); row.addWidget(export)
        view.addLayout(row); self.table = QTableWidget(0, 8); self.table.setHorizontalHeaderLabels(["Invoice Number", "Vendor", "Date", "Subtotal", "Tax", "Total", "Status", "Source File"]); self.table.setSelectionBehavior(QTableWidget.SelectRows); set_table_defaults(self.table); self.table.cellDoubleClicked.connect(self._detail); view.addWidget(self.table); return widget

    def _review(self):
        widget, view = self._page("Review", "Open a result to correct fields or explicitly verify it as a financial transaction.")
        self.review_text = QLabel("No records require review."); self.review_text.setWordWrap(True); view.addWidget(self.review_text); view.addStretch(); return widget

    def _transaction_page(self, title, kinds, key):
        widget, view = self._page(title, "Only verified financial transactions are listed. Invoice documents alone are not treated as cash movement.")
        controls = QHBoxLayout(); search = QLineEdit(); search.setPlaceholderText("Search counterparty, reference or category"); add_button=QPushButton("Add transaction",objectName="primary"); add_button.clicked.connect(lambda checked=False, default=self._default_transaction_type(key): self._open_transaction(default)); export_csv_button = QPushButton("Export CSV"); export_xlsx_button = QPushButton("Export Excel")
        controls.addWidget(search); controls.addWidget(add_button); controls.addWidget(export_csv_button); controls.addWidget(export_xlsx_button); view.addLayout(controls)
        table = QTableWidget(0, 7); table.setHorizontalHeaderLabels(["Date", "Type", "Counterparty", "Category", "Amount", "Payment status", "Source"]); table.setSelectionBehavior(QTableWidget.SelectRows); set_table_defaults(table); view.addWidget(table)
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
        widget, view = self._page("Customers & Suppliers", "Maintain contact records without changing historical transactions. Financial totals continue to come from the verified ledger.")
        controls = QHBoxLayout()
        self.party_search = QLineEdit(); self.party_search.setPlaceholderText("Search name, phone, email or GSTIN")
        add_customer = QPushButton("Add customer", objectName="primary"); add_supplier = QPushButton("Add supplier")
        controls.addWidget(self.party_search); controls.addWidget(add_customer); controls.addWidget(add_supplier); view.addLayout(controls)
        self.party_text = QLabel(); self.party_text.setWordWrap(True); view.addWidget(self.party_text)
        self.party_table = QTableWidget(0, 7); self.party_table.setHorizontalHeaderLabels(["Name", "Role", "Phone", "Email", "GSTIN", "Active", "Transactions"]); set_table_defaults(self.party_table); view.addWidget(self.party_table)
        add_customer.clicked.connect(lambda: self._edit_contact("customer")); add_supplier.clicked.connect(lambda: self._edit_contact("supplier"))
        self.party_search.textChanged.connect(self._refresh_parties_and_insights)
        self.party_table.cellDoubleClicked.connect(lambda row, _column: self._edit_contact_row(row))
        return widget

    def _edit_contact(self, role, existing=None):
        dialog=QDialog(self); dialog.setWindowTitle(("Edit " if existing else "Add ") + role); form=QFormLayout(dialog)
        fields={}
        for key,label in (("name","Name"),("phone","Phone"),("email","Email"),("address","Address"),("gstin","GSTIN (optional)"),("payment_terms","Payment terms"),("notes","Notes")):
            field=QLineEdit(str((existing or {}).get(key,""))); fields[key]=field; form.addRow(label,field)
        amount=QLineEdit(str((existing or {}).get("opening_balance","0.00"))); fields["opening_balance"]=amount; form.addRow("Opening balance",amount)
        buttons=QHBoxLayout(); save=QPushButton("Save",objectName="primary"); cancel=QPushButton("Cancel"); buttons.addWidget(save); buttons.addWidget(cancel); form.addRow(buttons)
        cancel.clicked.connect(dialog.reject)
        def persist():
            try:
                data=dict(existing or {}); data.update({key:field.text().strip() for key,field in fields.items()}); data["role"]=role
                ledger=LedgerStore(DB_PATH)
                try: ledger.save_contact(data)
                finally: ledger.close()
                dialog.accept(); self._refresh()
            except Exception as exc: QMessageBox.warning(dialog,"Contact not saved",str(exc))
        save.clicked.connect(persist); dialog.exec()

    def _edit_contact_row(self, row):
        items=[self.party_table.item(row,column) for column in range(self.party_table.columnCount())]
        contact_id=items[0].data(Qt.ItemDataRole.UserRole) if items[0] else None
        if not contact_id: return
        ledger=LedgerStore(DB_PATH)
        try: contact=next((item for item in ledger.list_contacts() if item["contact_id"]==contact_id),None)
        finally: ledger.close()
        if contact: self._edit_contact(contact["role"],contact)

    def _aging_page(self, role):
        title="Receivables Aging" if role=="receivable" else "Payables Aging"
        widget, view=self._page(title,"Outstanding balances use actual invoice due dates and explicit payment allocations. Missing due dates are shown as not due.")
        controls=QHBoxLayout(); as_of=QDateEdit(QDate.currentDate()); as_of.setCalendarPopup(True); as_of.setDisplayFormat("dd MMM yyyy"); refresh=QPushButton("Refresh",objectName="primary"); controls.addWidget(QLabel("As of")); controls.addWidget(as_of); controls.addWidget(refresh); controls.addStretch(); view.addLayout(controls)
        table=QTableWidget(0,9); table.setHorizontalHeaderLabels(["Customer / supplier","Invoice","Invoice date","Due date","Original","Allocated","Outstanding","Days overdue","Bucket"]); set_table_defaults(table); view.addWidget(table)
        summary=QLabel(); summary.setWordWrap(True); view.addWidget(summary); view.addStretch()
        setattr(self, f"{role}_aging_date", as_of); setattr(self, f"{role}_aging_table", table); setattr(self, f"{role}_aging_summary", summary)
        refresh.clicked.connect(lambda: self._refresh_aging(role)); as_of.dateChanged.connect(lambda: self._refresh_aging(role))
        return widget

    def _refresh_aging(self, role):
        table=getattr(self,f"{role}_aging_table",None)
        if table is None: return
        ledger=LedgerStore(DB_PATH)
        try: rows=build_aging(ledger,getattr(self,f"{role}_aging_date").date().toPython(),role)
        finally: ledger.close()
        table.setRowCount(len(rows))
        for index,row in enumerate(rows):
            values=(row.party,row.reference,row.invoice_date,row.due_date,row.original,row.allocated,row.outstanding,row.days_overdue if row.days_overdue is not None else "—",row.bucket)
            for column,value in enumerate(values):
                cell=QTableWidgetItem(f"{value:,.2f}" if isinstance(value,Decimal) else str(value))
                cell.setData(Qt.ItemDataRole.UserRole,row.source_id); table.setItem(index,column,cell)
        total=sum((row.outstanding for row in rows),Decimal("0.00"))
        summary=getattr(self,f"{role}_aging_summary"); summary.setText(f"{len(rows)} outstanding item(s) · Total outstanding: {total:,.2f} INR")
        table.resizeColumnsToContents()

    def _import_history_page(self):
        widget,view=self._page("Import History","Immutable import provenance from confirmed CSV/XLSX batches. Invalid and duplicate rows remain visible in the batch summary.")
        refresh=QPushButton("Refresh import history",objectName="primary"); refresh.clicked.connect(self._refresh_import_history); view.addWidget(refresh)
        self.import_history_table=QTableWidget(0,10); self.import_history_table.setHorizontalHeaderLabels(["ID","Filename","Type","Total","Imported","Rejected","Duplicates","Status","Created","Errors"]); set_table_defaults(self.import_history_table); view.addWidget(self.import_history_table); view.addStretch()
        return widget

    def _refresh_import_history(self):
        if not hasattr(self,"import_history_table"): return
        ledger=LedgerStore(DB_PATH)
        try: rows=ledger.list_import_batches()
        finally: ledger.close()
        self.import_history_table.setRowCount(len(rows))
        for index,item in enumerate(rows):
            errors=item.get("error_details_json","[]")
            values=(item["import_batch_id"],item["file_name"],item["import_type"],item.get("total_rows",item["record_count"]),item.get("successful_rows",item["record_count"]),item.get("rejected_rows",0),item.get("duplicate_rows",0),item["status"],item["created_at"],item.get("error_details_json","[]"))
            for column,value in enumerate(values): self.import_history_table.setItem(index,column,QTableWidgetItem(str(value)))
        self.import_history_table.resizeColumnsToContents()

    def _settings_page(self):
        widget,view=self._page("Settings & Data","Configure the business profile, preferences, backups, exports and local data maintenance.")
        tabs=QTabWidget(); profile=QWidget(); profile_form=QFormLayout(profile); self.settings_fields={}
        for key,label in (("name","Business name"),("owner_name","Owner name"),("business_type","Business type"),("address","Address"),("phone","Phone"),("email","Email"),("gstin","GSTIN"),("base_currency","Currency"),("financial_year_start","Financial year start month"),("payment_terms","Default payment terms")):
            field=QComboBox() if key=="business_type" else QLineEdit()
            if key=="business_type": field.addItems(["Retail shop","Restaurant/cafe","Wholesale/distribution","Service business","Other"])
            self.settings_fields[key]=field; profile_form.addRow(label,field)
        save_profile=QPushButton("Save business profile",objectName="primary"); save_profile.clicked.connect(self._save_profile); profile_form.addRow(save_profile)
        appearance=QWidget(); appearance_form=QFormLayout(appearance); self.theme_choice=QComboBox(); self.theme_choice.addItem("Light","light"); self.theme_choice.addItem("Dark","dark"); self.theme_choice.addItem("System default","system"); self.theme_choice.setCurrentIndex(max(0,self.theme_choice.findData(self._setting("theme","light")))); appearance_form.addRow("Theme",self.theme_choice); apply_theme=QPushButton("Apply appearance",objectName="primary"); apply_theme.clicked.connect(self._apply_theme); appearance_form.addRow(apply_theme)
        data=QWidget(); data_layout=QVBoxLayout(data); self.storage_summary=QLabel(); self.storage_summary.setWordWrap(True); data_layout.addWidget(self.storage_summary); backup=QPushButton("Create verified backup",objectName="primary"); restore=QPushButton("Restore backup"); integrity=QPushButton("Check database integrity"); export=QPushButton("Export verified transactions"); history=QPushButton("Refresh storage statistics"); [data_layout.addWidget(button) for button in (backup,restore,integrity,export,history)]; backup.clicked.connect(self._backup_database); restore.clicked.connect(self._restore_database); integrity.clicked.connect(self._check_integrity); export.clicked.connect(lambda: self._export_transactions("transactions","csv")); history.clicked.connect(self._refresh_storage_summary)
        about=QWidget(); about_layout=QVBoxLayout(about); logo=QLabel(); logo.setPixmap(logo_pixmap(120)); about_layout.addWidget(logo); about_layout.addWidget(QLabel(f"InvoiceFlow {APP_VERSION}\nLocal-first desktop financial operations.\nDatabase: {DB_PATH}"));
        tabs.addTab(profile,"Business profile"); tabs.addTab(appearance,"Appearance"); tabs.addTab(data,"Data management"); tabs.addTab(about,"About")
        view.addWidget(tabs); self._load_profile(); self._refresh_storage_summary(); return widget

    def _load_profile(self):
        ledger=LedgerStore(DB_PATH)
        try: profile=ledger.get_business_profile()
        finally: ledger.close()
        for key,field in self.settings_fields.items():
            value=profile.get(key,"")
            if isinstance(field,QComboBox):
                index=field.findText(str(value))
                if index>=0: field.setCurrentIndex(index)
            else: field.setText(str(value or ""))

    def _save_profile(self):
        try:
            values={}
            for key,field in self.settings_fields.items(): values[key]=field.currentText() if isinstance(field,QComboBox) else field.text().strip()
            if not values["name"]: raise ValueError("Business name is required")
            ledger=LedgerStore(DB_PATH)
            try: ledger.update_business_profile(**values); ledger.set_setting("onboarding_complete","1")
            finally: ledger.close()
            QMessageBox.information(self,"Profile saved","Business profile saved.")
            self._refresh()
        except Exception as exc: QMessageBox.warning(self,"Profile not saved",str(exc))

    def _apply_theme(self):
        preference=self.theme_choice.currentData()
        ledger=LedgerStore(DB_PATH)
        try: ledger.set_setting("theme",preference)
        finally: ledger.close()
        self.setStyleSheet(stylesheet(preference))
        self.theme_preference = preference
        self._apply_chart_theme(preference)

    def _refresh_storage_summary(self):
        if not hasattr(self,"storage_summary"): return
        ledger=LedgerStore(DB_PATH)
        try:
            tx_count=ledger.conn.execute("SELECT COUNT(*) FROM financial_transactions").fetchone()[0]
            contact_count=ledger.conn.execute("SELECT COUNT(*) FROM contacts").fetchone()[0]
            imports=ledger.conn.execute("SELECT COUNT(*) FROM ledger_import_batches").fetchone()[0]
            invoices=self.store.conn.execute("SELECT COUNT(*) FROM records").fetchone()[0]
            backups=ledger.list_backups()
        finally: ledger.close()
        size=Path(DB_PATH).stat().st_size if Path(DB_PATH).exists() else 0
        last_backup=backups[0]["created_at"] if backups else "No backup recorded"
        self.storage_summary.setText(f"Database: {DB_PATH}\nDatabase size: {size:,} bytes\nSaved invoice/document records: {invoices:,}\nFinancial transactions: {tx_count:,}\nCustomers and suppliers: {contact_count:,}\nImport batches: {imports:,}\nLast backup: {last_backup}")

    def _backup_database(self):
        destination,_=QFileDialog.getSaveFileName(self,"Create InvoiceFlow backup",str(Path.home()/f"invoiceflow-backup-{datetime.now():%Y%m%d-%H%M%S}.db"),"SQLite database (*.db)")
        if not destination: return
        target=Path(destination)
        if target.exists(): QMessageBox.warning(self,"Backup exists","Choose a new filename; existing backups are never overwritten."); return
        try:
            ledger=LedgerStore(DB_PATH)
            try: ledger.backup_to(target); integrity=sqlite3.connect(target).execute("PRAGMA integrity_check").fetchone()[0]=="ok"; ledger.record_backup(target,integrity)
            finally: ledger.close()
            if not integrity: raise ValueError("SQLite integrity check failed")
            QMessageBox.information(self,"Backup complete",f"Verified backup saved to {target}")
            self._refresh_storage_summary()
        except Exception as exc: QMessageBox.critical(self,"Backup failed",str(exc))

    def _restore_database(self):
        source,_=QFileDialog.getOpenFileName(self,"Select InvoiceFlow backup",str(Path.home()),"SQLite database (*.db *.sqlite)")
        if not source: return
        answer=QMessageBox.question(self,"Replace current database","Restoring replaces the current database. A safety backup will be created first. Continue?")
        if answer!=QMessageBox.StandardButton.Yes: return
        safety=Path(DB_PATH).with_name(f"{Path(DB_PATH).stem}-before-restore-{datetime.now():%Y%m%d-%H%M%S}.db")
        try:
            source_conn=sqlite3.connect(source); valid=source_conn.execute("PRAGMA integrity_check").fetchone()[0]=="ok"; source_conn.close()
            if not valid: raise ValueError("Selected file failed SQLite integrity validation")
            current=LedgerStore(DB_PATH)
            try: current.backup_to(safety)
            finally: current.close()
            restored=Path(DB_PATH).with_suffix(".restore")
            LedgerStore.restore_from(source,restored)
            restored.replace(DB_PATH)
            QMessageBox.information(self,"Restore complete","Database restored and integrity-validated. Restart InvoiceFlow before continuing.")
        except Exception as exc: QMessageBox.critical(self,"Restore failed",f"Original data was preserved. {exc}")

    def _check_integrity(self):
        try:
            connection=sqlite3.connect(DB_PATH); result=connection.execute("PRAGMA integrity_check").fetchone()[0]; foreign=connection.execute("PRAGMA foreign_key_check").fetchall(); connection.close()
            QMessageBox.information(self,"Database integrity",f"SQLite integrity: {result}\nForeign-key issues: {len(foreign)}")
        except Exception as exc: QMessageBox.critical(self,"Integrity check failed",str(exc))

    def _maybe_onboard(self):
        ledger=LedgerStore(DB_PATH)
        try:
            complete=ledger.get_setting("onboarding_complete","")
            has_data=ledger.conn.execute("SELECT COUNT(*) FROM financial_transactions").fetchone()[0] or ledger.conn.execute("SELECT COUNT(*) FROM contacts").fetchone()[0]
            if not complete and has_data: ledger.set_setting("onboarding_complete","1"); complete="1"
        finally: ledger.close()
        if complete: return
        from .onboarding import OnboardingDialog
        self.onboarding=OnboardingDialog(DB_PATH,self)
        self.onboarding.finished.connect(lambda _result: self._load_profile() if hasattr(self,"settings_fields") else None)
        self.onboarding.show()

    def _insights_page(self):
        widget, view = self._page("Business Insights", "These are deterministic findings based on verified records, not fraud conclusions or generic AI advice.")
        self.insight_text = QLabel("No insights are available until verified transactions exist."); self.insight_text.setWordWrap(True); view.addWidget(self.insight_text); view.addStretch(); return widget

    def _refresh_parties_and_insights(self):
        ledger = LedgerStore(DB_PATH)
        try:
            transactions = ledger.list(verified_only=True)
            budgets = ledger.list_budgets(active_only=True)
            contacts = ledger.list_contacts()
        finally:
            ledger.close()
        period = period_for("last_12_months")
        snapshot = build_analytics(transactions, period, "INR", previous_period(period), budgets=budgets)
        activity={}
        for item in snapshot.customers+snapshot.suppliers:
            activity[(item["name"].casefold(), "customer" if item in snapshot.customers else "supplier")]=len(item["source_ids"])
        rows = contacts
        self.party_table.setRowCount(len(rows))
        term=self.party_search.text().casefold() if hasattr(self,"party_search") else ""
        rows=[item for item in rows if not term or term in " ".join(str(item.get(key,"")) for key in ("name","phone","email","gstin")).casefold()]
        self.party_table.setRowCount(len(rows))
        self.party_text.setText(f"Customers: {sum(item['role']=='customer' for item in rows)}   Suppliers: {sum(item['role']=='supplier' for item in rows)}   Verified activity period: {period.label}")
        for row, item in enumerate(rows):
            values=(item["name"],item["role"].title(),item.get("phone") or "—",item.get("email") or "—",item.get("gstin") or "—","Yes" if item.get("active",1) else "No",activity.get((item["name"].casefold(),item["role"]),0))
            for column, value in enumerate(values):
                cell=QTableWidgetItem(str(value))
                if column==0: cell.setData(Qt.ItemDataRole.UserRole,item["contact_id"])
                self.party_table.setItem(row,column,cell)
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
        item = items[row]; ledger=LedgerStore(DB_PATH)
        try:
            batch=ledger.conn.execute("SELECT b.file_name,b.import_batch_id,t.import_row_number FROM financial_transactions t LEFT JOIN ledger_import_batches b ON b.import_batch_id=t.import_batch_id WHERE t.transaction_id=?",(item.transaction_id,)).fetchone()
            audit=ledger.conn.execute("SELECT action,changed_at FROM transaction_audit WHERE transaction_id=? ORDER BY audit_id",(item.transaction_id,)).fetchall()
            allocations=ledger.list_allocations(item.transaction_id)
        finally: ledger.close()
        dialog=QDialog(self); dialog.setWindowTitle(f"Transaction {item.transaction_id}"); dialog.resize(640,520); layout=QVBoxLayout(dialog)
        allocation_lines="\n".join(f"{a['status']} {a['amount']} {a['currency']} · invoice {a['invoice_reference'] or a['invoice_transaction_id']}" for a in allocations) or "No payment allocations"
        source_info=f"Source: {item.source_file or 'Not recorded'}"
        if batch and batch["import_batch_id"]: source_info+=f"\nImport batch: {batch['import_batch_id']} · row {batch['import_row_number']}"
        history="\n".join(f"{a['changed_at']} · {a['action']}" for a in audit)
        summary=QLabel(f"ID: {item.transaction_id}\nType: {item.transaction_type}\nDate: {item.transaction_date}\nAmount: {item.amount} {item.currency}\nCounterparty: {item.counterparty or 'Not recorded'}\nCategory: {item.category or 'Not recorded'}\nReference: {item.reference_number or 'Not recorded'}\nStatus: {item.verification_status}\n{source_info}\n\nPayment allocations:\n{allocation_lines}\n\nAudit history:\n{history}"); summary.setWordWrap(True); layout.addWidget(summary)
        controls=QHBoxLayout(); edit=QPushButton("Edit transaction"); reverse=QPushButton("Reverse transaction"); close=QPushButton("Close"); controls.addWidget(edit); controls.addWidget(reverse); controls.addStretch(); controls.addWidget(close); layout.addLayout(controls)
        close.clicked.connect(dialog.reject)
        def edit_item():
            if allocations and any(a["status"]=="ACTIVE" for a in allocations): QMessageBox.warning(dialog,"Reverse allocation first","This transaction has an active payment allocation. Reverse that allocation before editing the amount or counterparty."); return
            form=TransactionDialog(item.transaction_type,dialog,item)
            if form.exec():
                store=LedgerStore(DB_PATH)
                try: store.update_transaction(form._transaction)
                finally: store.close()
                dialog.accept(); self._refresh()
        def reverse_item():
            reason,ok=QInputDialog.getText(dialog,"Reverse transaction","Reason for reversal:")
            if not ok: return
            store=LedgerStore(DB_PATH)
            try: store.reverse(item.transaction_id,reason)
            except Exception as exc: QMessageBox.warning(dialog,"Could not reverse transaction",str(exc)); return
            finally: store.close()
            dialog.accept(); self._refresh()
        edit.clicked.connect(edit_item); reverse.clicked.connect(reverse_item); dialog.exec()

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
        view.addLayout(form);         self.budget_table = QTableWidget(0, 6); self.budget_table.setHorizontalHeaderLabels(["Category", "Start", "End", "Budget", "Currency", "Active"]); self.budget_table.setSelectionBehavior(QTableWidget.SelectRows); set_table_defaults(self.budget_table); self.budget_table.cellDoubleClicked.connect(self._load_budget); view.addWidget(self.budget_table); view.addStretch(); return widget

    def _navigate(self, label, push=True):
        pages = {"Home": (self.home, "Home"), "Overview": (self.overview, "Business Overview"), "Analytics": (self.analytics, "Analytics"), "Process Invoices": (self.process, "Invoices & Documents"), "Results": (self.results, "Results"), "Review": (self.review, "Review"), "Reports": (self.reports, "Reports & Analytics"), "Budgets": (self.budgets, "Budgets & Targets"), "Settings": (self.settings, "Settings & Data"), "About": (self.about, "About InvoiceFlow"), "Sales": (self.sales, "Sales & Income"), "Purchases": (self.purchases, "Purchases & Expenses"), "Expenses": (self.expenses, "Expenses"), "Money Received": (self.received, "Money Received"), "Money Paid": (self.paid, "Money Paid"), "Receivables": (self.receivables, "Receivables Aging"), "Payables": (self.payables, "Payables Aging"), "Transactions": (self.transactions, "Transactions"), "Customers & Suppliers": (self.parties, "Customers & Suppliers"), "Business Insights": (self.insights, "Business Insights"), "Import Data": (self.import_page, "Import Financial Data"), "Import History": (self.import_history, "Import History"), "Reconciliation": (self.reconciliation, "Payment Reconciliation")}
        if label not in pages: return
        if label == "Home": self._navigation.clear(); push=False
        if push and label != self._current_page: self._navigation.append(self._current_page)
        widget, title = pages[label]; self.stack.setCurrentWidget(widget); self.location.setText(title); self._current_page=label
        for page, buttons in self.sidebar_buttons.items():
            for button in buttons:
                button.setChecked(page == label)
        self._refresh()

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
            self._update_home_dashboard(snapshot, transactions)
        except Exception as exc:
            self.overview_text.setText(f"Unable to refresh overview: {exc}")

    def _update_home_dashboard(self, snapshot, transactions):
        if not hasattr(self, "home_kpis"):
            return
        self.home_date.setText(QDate.currentDate().toString("dd MMM yyyy"))
        self.stats.setText(
            f"{len(transactions):,} verified transaction(s) in the selected period · "
            f"{snapshot.period.label}"
            if transactions else
            "No verified financial records yet. Start with an invoice upload, import, or manual transaction."
        )
        for key in ("sales", "expenses", "gross_profit", "collections"):
            metric = snapshot.kpis[key]["value"]
            self.home_kpis[key].setText("Unavailable" if metric is None else f"{metric:,.2f} {snapshot.currency}")
        ledger = LedgerStore(DB_PATH)
        try:
            receivables = sum((ledger.allocation_summary(tx.transaction_id)["remaining"] for tx in transactions if tx.transaction_type == "sale"), start=0)
            payables = sum((ledger.allocation_summary(tx.transaction_id)["remaining"] for tx in transactions if tx.transaction_type == "purchase"), start=0)
        finally:
            ledger.close()
        self.home_kpis["receivables"].setText(f"{receivables:,.2f} INR")
        self.home_kpis["payables"].setText(f"{payables:,.2f} INR")
        self.home_revenue_chart.set_monthly(snapshot.monthly, self._show_source_transactions)
        self.home_expense_chart.set_categories(snapshot.expense_categories, self._show_source_transactions)
        if snapshot.expense_categories:
            largest = max(snapshot.expense_categories, key=lambda row: row.get("amount", 0))
            self.home_budget_text.setText(
                f"Highest operating expense: {largest.get('category', 'Uncategorized')} · "
                f"{largest.get('amount', 0):,.2f} {snapshot.currency}. "
                "Set an active budget to compare planned and actual spending."
            )
        else:
            self.home_budget_text.setText(
                "No operating expenses are available for this period. Add an expense or import financial data to activate budget monitoring."
            )
        recent = sorted(transactions, key=lambda item: (item.transaction_date, item.transaction_id or 0), reverse=True)[:8]
        self.home_activity.setRowCount(len(recent))
        for row, item in enumerate(recent):
            values = (item.transaction_date, item.transaction_type.replace("_", " ").title(), item.counterparty or "—", f"{item.amount:,.2f} {item.currency}" if item.amount is not None else "—")
            for column, value in enumerate(values):
                self.home_activity.setItem(row, column, QTableWidgetItem(str(value)))

    def _refresh_analytics(self):
        try:
            kind = self.analytics_period.currentData()
            anchor = self.analytics_anchor.date().toPython()
            period = period_between(self.analytics_start.date().toPython(), anchor) if kind == "custom" else period_for(kind, anchor)
            ledger = LedgerStore(DB_PATH)
            try:
                transactions = ledger.list(verified_only=True)
                budgets = ledger.list_budgets(active_only=True)
                snapshot = build_analytics(transactions, period, "INR", previous_period(period), budgets=budgets)
                receivables = sum((ledger.allocation_summary(tx.transaction_id)["remaining"] for tx in snapshot.transactions if tx.transaction_type == "sale"), start=0)
                payables = sum((ledger.allocation_summary(tx.transaction_id)["remaining"] for tx in snapshot.transactions if tx.transaction_type == "purchase"), start=0)
            finally:
                ledger.close()
            self.analytics_period_label.setText(
                f"{period.label} · {period.start.isoformat()} to {period.end.isoformat()} · "
                f"Showing {snapshot.granularity} analysis from {len(snapshot.transactions)} verified transaction(s)."
            )
            for key in ("sales", "purchases", "expenses", "gross_profit", "collections", "payments"):
                metric = snapshot.kpis[key]
                value = metric["value"]
                display = "Unavailable" if value is None else f"{value:,.2f} {snapshot.currency}"
                if metric["change"] is not None:
                    display += f"  {metric['change']:+.1%}"
                self.analytics_kpi_values[key].setText(display)
            self.analytics_kpi_values["receivables"].setText(f"{receivables:,.2f} INR")
            self.analytics_kpi_values["payables"].setText(f"{payables:,.2f} INR")
            self.analytics_quality.setText(
                "Data quality: " + " · ".join(snapshot.data_quality)
                if snapshot.data_quality else "Data quality: verified records are complete for the selected calculations."
            )
            self.analytics_revenue_chart.set_revenue_expenses(snapshot.series, self._analytics_bar_detail)
            self.analytics_expense_chart.set_categories(snapshot.expense_categories, self._show_source_transactions)
            self.analytics_cash_chart.set_cash_movement(snapshot.series, self._analytics_bar_detail)
            self.analytics_trend_chart.set_line(snapshot.series, "sales", "Revenue", self._analytics_point_detail)
            self.analytics_budget_chart.set_budget_utilization(snapshot.budget_utilization, self._budget_bar_detail)
            if snapshot.budget_utilization:
                self.analytics_budget_summary.setText(
                    "Budget performance: " + " · ".join(
                        f"{row['category']} {row['utilization']:.1%}" if row["utilization"] is not None else f"{row['category']} not measurable"
                        for row in snapshot.budget_utilization
                    )
                )
            else:
                self.analytics_budget_summary.setText("No active budgets overlap the selected period.")
            self._fill_analytics_table(self.analytics_customers, snapshot.customers, "name", "amount")
            self._fill_analytics_table(self.analytics_suppliers, snapshot.suppliers, "name", "amount")
            recent = sorted(snapshot.transactions, key=lambda item: (item.transaction_date, item.transaction_id or 0), reverse=True)[:10]
            self.analytics_transactions.setRowCount(len(recent))
            for row, item in enumerate(recent):
                values = (item.transaction_date, item.transaction_type.replace("_", " ").title(), item.counterparty or "—", f"{item.amount:,.2f} {item.currency}" if item.amount is not None else "—")
                for column, value in enumerate(values):
                    self.analytics_transactions.setItem(row, column, QTableWidgetItem(str(value)))
            if snapshot.insights:
                self.analytics_insights.setText("\n\n".join(f"{item['finding']}\n{item['action']}" for item in snapshot.insights))
            elif snapshot.budget_utilization:
                self.analytics_insights.setText(
                    "Budget utilization is shown in the dedicated chart above. "
                    "Negative remaining values indicate an overrun."
                )
            else:
                self.analytics_insights.setText("No financial insights or active budgets for this period.")
        except Exception as exc:
            self.analytics_period_label.setText(f"Unable to refresh analytics: {exc}")
            self.analytics_quality.setText("Correct the issue and refresh Analytics.")

    @staticmethod
    def _fill_analytics_table(table, rows, name_key, amount_key):
        limited = rows[:8]
        table.setRowCount(len(limited))
        for row, item in enumerate(limited):
            table.setItem(row, 0, QTableWidgetItem(str(item.get(name_key, "Unassigned"))))
            table.setItem(row, 1, QTableWidgetItem(f"{item.get(amount_key, 0):,.2f}"))

    def _analytics_bar_detail(self, row, key, _hovered):
        source_key = f"{key}_source_ids"
        self._show_source_transactions(row.get(source_key, []), key.title(), row.get(key, 0))

    def _analytics_point_detail(self, row, _hovered):
        self._show_source_transactions(row.get("sales_source_ids", []), "Revenue", row.get("sales", 0))

    def _budget_bar_detail(self, row, key, _clicked):
        self._show_source_transactions(row.get("source_ids", []), f"{row.get('category', 'Budget')} {key}", row.get(key, 0))

    def _refresh_financial_views(self, *_):
        if getattr(self, "_syncing_views", False): return
        self._syncing_views=True
        try:
            if hasattr(self,"overview_text"): self._refresh_overview()
            if hasattr(self,"analytics_text"): self._refresh_analytics()
        finally: self._syncing_views=False

    def _show_source_transactions(self, source_ids, label="Chart records", expected=None):
        ids = {int(value) for value in source_ids if value}
        ledger = LedgerStore(DB_PATH)
        try: items = [tx for tx in ledger.list(verified_only=True) if tx.transaction_id in ids]
        finally: ledger.close()
        dialog = QDialog(self); dialog.setWindowTitle(f"Transactions — {label}"); dialog.resize(760, 430); layout = QVBoxLayout(dialog)
        total = sum((-(tx.amount or 0) if tx.transaction_type == "sales_return" and label.casefold() == "sales" else (tx.amount or 0) for tx in items), start=0)
        layout.addWidget(QLabel(f"{label} · {len(items)} transaction(s) · listed amount sum {total:,.2f}" + (f" · chart value {expected:,.2f}" if expected is not None else "")))
        table = QTableWidget(len(items), 7); table.setHorizontalHeaderLabels(["Date", "Type", "Party", "Reference", "Amount", "Status", "Source document"])
        for row, tx in enumerate(items):
            values = (tx.transaction_date, tx.transaction_type, tx.counterparty, tx.reference_number, tx.amount, tx.verification_status, Path(tx.source_file).name if tx.source_file else "")
            for col, value in enumerate(values): table.setItem(row, col, QTableWidgetItem(str(value or "")))
        table.resizeColumnsToContents(); layout.addWidget(table)
        open_source = QPushButton("Open selected source document"); layout.addWidget(open_source)
        def open_selected():
            row=table.currentRow()
            if row < 0 or not items[row].source_file: QMessageBox.information(dialog,"Source unavailable","No source document is linked to this transaction."); return
            path=Path(items[row].source_file)
            if path.exists(): QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
            else: QMessageBox.warning(dialog,"Source unavailable",f"The linked file could not be found:\n{path}")
        open_source.clicked.connect(open_selected); dialog.exec()

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
        if hasattr(self, "recon_invoices"): self._refresh_reconciliation()
        if hasattr(self, "analytics_text"): self._refresh_analytics()
        if hasattr(self,"receivable_aging_table"): self._refresh_aging("receivable")
        if hasattr(self,"payable_aging_table"): self._refresh_aging("payable")
        if hasattr(self,"import_history_table"): self._refresh_import_history()
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
