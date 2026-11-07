import pytest
pytest.importorskip("PySide6")
from gui.main_window import MainWindow
from gui.charts import FinancialChart

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
