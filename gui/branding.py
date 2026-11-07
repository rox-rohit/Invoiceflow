from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPixmap


def asset_path(name: str) -> Path:
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
    return root / "assets" / "brand" / name


def logo_pixmap(size: int | None = None) -> QPixmap:
    pixmap = QPixmap(str(asset_path("invoiceflow-if-logo.png")))
    if size:
        pixmap = pixmap.scaled(
            size,
            size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
    return pixmap


def application_icon() -> QIcon:
    return QIcon(str(asset_path("invoiceflow-if-logo.ico")))
