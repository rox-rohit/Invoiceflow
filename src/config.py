from pathlib import Path
import os

APP_NAME="InvoiceFlow"
APP_VERSION="2.3.1"
DATA_DIR=Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / APP_NAME
DB_PATH=DATA_DIR / "history.db"
