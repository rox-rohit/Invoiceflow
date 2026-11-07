import sys
from PySide6.QtWidgets import QApplication, QSplashScreen
from gui.main_window import MainWindow
from gui.branding import application_icon, logo_pixmap
from src.config import APP_VERSION

def main():
    app=QApplication(sys.argv)
    app.setApplicationName("InvoiceFlow")
    app.setApplicationVersion(APP_VERSION)
    app.setWindowIcon(application_icon())
    splash=QSplashScreen(logo_pixmap(280))
    splash.show()
    app.processEvents()
    window=MainWindow()
    window.show()
    splash.finish(window)
    return app.exec()

if __name__ == "__main__": raise SystemExit(main())
