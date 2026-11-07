import pytest
pytest.importorskip("PySide6")
from gui.main_window import MainWindow
from gui.charts import FinancialChart
from gui.transaction_dialog import TransactionDialog
from src.ledger import LedgerStore
from PySide6.QtWidgets import QDialog

def test_main_window_initializes(qtbot, monkeypatch, tmp_path):
    monkeypatch.setattr("gui.main_window.DB_PATH", tmp_path / "history.db")
    window = MainWindow(); qtbot.addWidget(window)
    assert "InvoiceFlow" in window.windowTitle()
    assert window.minimumWidth() >= 1000
    window.nav[1].click()
    assert window.stack.currentWidget() is window.process
    window._navigate("Reports")
    assert window.report_period.currentData() == "month"
    window.report_period.setCurrentIndex(3)
    assert window.report_period.currentData() == "last_6_months"
    window._navigate("Home")
    assert window.stack.currentWidget() is window.home
    chart=FinancialChart("Test chart"); qtbot.addWidget(chart); chart.set_monthly([{"month":"2026-01","sales":100,"expenses":40}]); assert chart.chart.series()

def test_back_stack_and_manual_transaction_dialog(qtbot, monkeypatch, tmp_path):
    monkeypatch.setattr("gui.main_window.DB_PATH", tmp_path / "history.db")
    window=MainWindow(); qtbot.addWidget(window)
    window._navigate("Analytics"); assert window._current_page == "Analytics"; window._back(); assert window._current_page == "Home"
    dialog=TransactionDialog("expense",window); qtbot.addWidget(dialog); dialog.fields["amount"].setText("125.50"); dialog.fields["category"].setText("Utilities"); dialog.accept(); assert dialog.result() == QDialog.DialogCode.Accepted
    store=LedgerStore(tmp_path / "history.db"); transaction=dialog._transaction; store.add(transaction); assert store.list(verified_only=True)[0].amount == transaction.amount; store.close()
