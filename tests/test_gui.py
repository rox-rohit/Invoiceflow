import pytest
pytest.importorskip("PySide6")
from gui.main_window import MainWindow

def test_main_window_initializes(qtbot, monkeypatch, tmp_path):
    monkeypatch.setattr("gui.main_window.DB_PATH", tmp_path / "history.db")
    window = MainWindow(); qtbot.addWidget(window)
    assert "InvoiceFlow" in window.windowTitle()
    assert window.minimumWidth() >= 1000
    window.nav[1].click()
    assert window.stack.currentWidget() is window.process
