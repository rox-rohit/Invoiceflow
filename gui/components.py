from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QSizePolicy, QVBoxLayout, QWidget


def section_title(text: str, parent: QWidget | None = None) -> QLabel:
    label = QLabel(text, parent)
    label.setObjectName("sectionTitle")
    return label


def card(parent: QWidget | None = None, object_name: str = "surfaceCard") -> QFrame:
    frame = QFrame(parent)
    frame.setObjectName(object_name)
    frame.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    return frame


def empty_state(text: str, parent: QWidget | None = None) -> QLabel:
    label = QLabel(text, parent)
    label.setObjectName("emptyState")
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    label.setWordWrap(True)
    label.setMinimumHeight(72)
    return label


def set_table_defaults(table) -> None:
    table.setAlternatingRowColors(True)
    table.setWordWrap(False)
    table.setSortingEnabled(True)
    table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
    table.verticalHeader().setDefaultSectionSize(34)
    table.verticalHeader().setVisible(False)
    table.horizontalHeader().setStretchLastSection(True)
    table.horizontalHeader().setMinimumSectionSize(90)
