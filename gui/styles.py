TOKENS = {
    "navy": "#172B4D",
    "teal": "#0F766E",
    "sage": "#6B8F71",
    "canvas": "#F5F7FA",
    "surface": "#FFFFFF",
    "surface_alt": "#F8FAFC",
    "text": "#172B4D",
    "muted": "#64748B",
    "border": "#E2E8F0",
    "border_strong": "#CBD5E1",
    "accent": "#0F766E",
    "accent_soft": "#E6F4F1",
    "success": "#15803D",
    "warning": "#B45309",
    "danger": "#B91C1C",
    "radius": "10px",
    "space": "12px",
}

STYLE = """
QMainWindow, QWidget {
    background: #F5F7FA;
    color: #172B4D;
    font-family: "Segoe UI";
    font-size: 10pt;
}
QFrame#sidebar {
    background: #FFFFFF;
    border-right: 1px solid #E2E8F0;
}
QPushButton#sidebarToggle {
    background: #F8FAFC;
    border: 1px solid #E2E8F0;
    border-radius: 6px;
    color: #64748B;
    padding: 5px;
    min-width: 24px;
    min-height: 24px;
}
QPushButton#sidebarToggle:hover {
    background: #E6F4F1;
    color: #0F766E;
    border-color: #9FD4CB;
}
QLabel#brand {
    color: #172B4D;
    font-size: 18pt;
    font-weight: 700;
}
QLabel#brandMark {
    color: #2563EB;
    font-size: 21pt;
    font-weight: 800;
}
QLabel#brandLogo {
    background: #FFFFFF;
}
QLabel#sidebarSection {
    color: #94A3B8;
    font-size: 8pt;
    font-weight: 700;
    letter-spacing: 1px;
    padding-top: 14px;
}
QPushButton#navButton {
    background: transparent;
    border: 0;
    border-radius: 6px;
    color: #64748B;
    padding: 9px 12px;
    text-align: left;
    font-weight: 600;
}
QPushButton#navButton:hover {
    background: #E6F4F1;
    color: #0F766E;
}
QPushButton#navButton:checked {
    background: #D7ECE7;
    color: #0B5F59;
}
QWidget#contentShell { background: #F5F7FA; }
QWidget#appHeader {
    background: #FFFFFF;
    border-bottom: 1px solid #E2E8F0;
}
QFrame#heroCard {
    background: #173B4A;
    border: 0;
    border-radius: 14px;
}
QLabel#heroTitle { color: #F8FAFC; font-size: 24pt; font-weight: 700; }
QLabel#heroSubtitle { color: #C5D8DB; font-size: 10pt; }
QLabel#heroDate { color: #D7ECE7; font-weight: 600; }
QPushButton#heroAction {
    background: #D7ECE7;
    color: #0B5F59;
    border: 0;
    border-radius: 7px;
    font-weight: 700;
}
QPushButton#heroAction:hover { background: #FFFFFF; }
QLabel#breadcrumb { color: #64748B; font-weight: 600; }
QLabel#pageTitle {
    color: #172B4D;
    font-size: 20pt;
    font-weight: 700;
}
QLabel#pageExplanation { color: #64748B; }
QLabel#sectionTitle {
    color: #172B4D;
    font-size: 12pt;
    font-weight: 700;
    padding-top: 8px;
}
QScrollArea#pageScroll { border: 0; background: transparent; }
QWidget#pageContent { background: transparent; }
QFrame#surfaceCard, QLabel#overviewCard {
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    padding: 14px;
}
QFrame#kpiCard {
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    padding: 14px;
}
QLabel#kpiLabel { color: #64748B; font-size: 9pt; font-weight: 600; }
QLabel#kpiValue { color: #172B4D; font-size: 16pt; font-weight: 700; }
QLabel#kpiHint { color: #94A3B8; font-size: 8pt; }
QLabel#kpiLabel, QLabel#kpiValue, QLabel#kpiHint { background: transparent; }
QLabel#emptyState { color: #64748B; background: #FFFFFF; border: 1px dashed #CBD5E1; border-radius: 8px; padding: 18px; }
QPushButton {
    background: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    color: #172B4D;
    padding: 8px 13px;
    min-height: 18px;
}
QPushButton:hover { border-color: #2563EB; color: #1D4ED8; }
QPushButton:pressed { background: #EFF6FF; }
QPushButton:disabled { color: #94A3B8; background: #F8FAFC; }
QPushButton#primary { background: #0F766E; border-color: #0F766E; color: #FFFFFF; font-weight: 600; }
QPushButton#primary:hover { background: #0B5F59; }
QFrame#metricCard {
    background: #FFFFFF;
    border: 1px solid #E5EAF0;
    border-radius: 12px;
}
QFrame#metricCard[accent="teal"] { border-top: 3px solid #2A9D8F; }
QFrame#metricCard[accent="amber"] { border-top: 3px solid #C08457; }
QFrame#metricCard[accent="navy"] { border-top: 3px solid #355C7D; }
QFrame#metricCard[accent="sage"] { border-top: 3px solid #5D946A; }
QFrame#metricCard[accent="blue"] { border-top: 3px solid #5B91F5; }
QFrame#metricCard[accent="purple"] { border-top: 3px solid #7568A8; }
QLabel#metricLabel { color: #64748B; font-size: 9pt; font-weight: 700; }
QLabel#metricValue { color: #172B4D; font-size: 20pt; font-weight: 700; padding-top: 5px; }
QLabel#metricHint { color: #94A3B8; font-size: 8pt; }
QLabel#metricBadge { color: #0F766E; background: #E6F4F1; border-radius: 4px; padding: 3px 5px; font-size: 7pt; font-weight: 800; }
QLabel#cardTitle { color: #172B4D; font-size: 11pt; font-weight: 700; }
QLabel#cardBody { color: #64748B; line-height: 1.3; }
QFrame#activityCard, QFrame#insightCard, QFrame#stepCard, QFrame#importCard {
    background: #FFFFFF;
    border: 1px solid #E5EAF0;
    border-radius: 12px;
}
QFrame#chartCard {
    background: #FFFFFF;
    border: 1px solid #E5EAF0;
    border-radius: 12px;
    padding: 5px;
}
QFrame#uploadCard {
    background: #FFFFFF;
    border: 2px dashed #9FD4CB;
    border-radius: 16px;
    min-height: 220px;
}
QLabel#uploadTitle { color: #172B4D; font-size: 18pt; font-weight: 700; }
QLabel#uploadHint { color: #64748B; font-size: 11pt; padding: 6px; }
QLabel#uploadMeta { color: #94A3B8; font-size: 8pt; padding-top: 8px; }
QLabel#stepNumber { color: #0F766E; font-size: 15pt; font-weight: 800; }
QPushButton#featureCard {
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    color: #172B4D;
    padding: 16px;
    text-align: left;
    font-weight: 600;
}
QPushButton#featureCard:hover { border-color: #93C5FD; background: #F8FAFC; }
QLineEdit, QComboBox, QDateEdit {
    background: #FFFFFF;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    padding: 7px 9px;
    min-height: 18px;
}
QLineEdit:focus, QComboBox:focus, QDateEdit:focus { border: 1px solid #2563EB; }
QTableWidget {
    background: #FFFFFF;
    alternate-background-color: #F8FAFC;
    border: 1px solid #E2E8F0;
    border-radius: 8px;
    gridline-color: #F1F5F9;
    selection-background-color: #DBEAFE;
    selection-color: #172B4D;
}
QHeaderView::section {
    background: #F8FAFC;
    color: #64748B;
    padding: 9px;
    border: 0;
    border-bottom: 1px solid #E2E8F0;
    font-weight: 700;
}
QProgressBar { background: #E2E8F0; border: 0; border-radius: 5px; height: 10px; text-align: center; }
QProgressBar::chunk { background: #2563EB; border-radius: 5px; }
QDialog { background: #F5F7FA; }
QToolTip {
    background: #172B4D;
    color: #FFFFFF;
    border: 1px solid #334155;
    padding: 6px;
}
"""
