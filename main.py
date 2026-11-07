import sys
from PySide6.QtWidgets import QApplication
from gui.main_window import MainWindow
from src.config import APP_VERSION

def main():
    app=QApplication(sys.argv); app.setApplicationName("InvoiceFlow"); app.setApplicationVersion(APP_VERSION); window=MainWindow(); window.show(); return app.exec()

if __name__ == "__main__": raise SystemExit(main())
