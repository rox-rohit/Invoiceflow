from __future__ import annotations

import os

from .styles import STYLE, TOKENS


def theme_name(preference: str) -> str:
    if preference != "system":
        return preference
    return "dark" if os.environ.get("INVOICEFLOW_SYSTEM_DARK", "").casefold() in {"1", "true", "dark"} else "light"


def stylesheet(preference: str) -> str:
    if theme_name(preference) == "light":
        return STYLE
    replacements = {
        "#F5F7FA": "#172033",
        "#FFFFFF": "#202B3D",
        "#172B4D": "#F1F5F9",
        "#64748B": "#B7C3D4",
        "#E2E8F0": "#3A475B",
        "#F8FAFC": "#263449",
        "#CBD5E1": "#52627A",
        "#F1F5F9": "#334155",
        "#EFF6FF": "#243B5A",
        "#DBEAFE": "#294B76",
        "#1D4ED8": "#8DB8FF",
        "#2563EB": "#5B91F5",
        "#93C5FD": "#6EA5FF",
        "#94A3B8": "#9AA9BC",
    }
    result = STYLE
    for source, target in replacements.items():
        result = result.replace(source, target)
    result += """
QFrame#heroCard { background: #102D39; }
QLabel#heroTitle { color: #F8FAFC; }
QLabel#heroSubtitle { color: #B9D0D3; }
QLabel#heroDate { color: #BFE8DE; }
QPushButton#heroAction { background: #2C514B; color: #C8F0E7; }
QFrame#metricCard, QFrame#activityCard, QFrame#insightCard, QFrame#stepCard, QFrame#importCard, QFrame#chartCard, QFrame#uploadCard { background: #202B3D; border-color: #3A475B; }
QLabel#metricLabel, QLabel#cardBody, QLabel#uploadHint { color: #B7C3D4; }
QLabel#metricValue, QLabel#cardTitle, QLabel#uploadTitle { color: #F1F5F9; }
QLabel#metricHint, QLabel#uploadMeta { color: #9AA9BC; }
QLabel#metricBadge { background: #2C514B; color: #C8F0E7; }
QLabel#stepNumber { color: #8FD5C8; }
QFrame#uploadCard { border-color: #4B877D; }
QPushButton#primary { background: #2A9D8F; border-color: #2A9D8F; color: #F8FAFC; }
QPushButton#primary:hover { background: #238276; }
QPushButton#navButton:hover { background: #244238; color: #A7E0D5; }
QPushButton#navButton:checked { background: #2C514B; color: #C8F0E7; }
QPushButton#sidebarToggle { background: #263449; border-color: #3A475B; color: #B7C3D4; }
QToolTip { background: #0F172A; color: #F8FAFC; border-color: #52627A; }
"""
    return result
