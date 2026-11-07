from __future__ import annotations

from PySide6.QtCharts import QBarCategoryAxis, QBarSeries, QBarSet, QCategoryAxis, QChart, QChartView, QLineSeries, QValueAxis
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QVBoxLayout, QWidget


class FinancialChart(QWidget):
    """Small reusable QtCharts view driven only by analytics-service data."""

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.title = title
        self.chart = QChart()
        self.chart.setTitle(title)
        self.chart.legend().setVisible(True)
        self.chart_view = QChartView(self.chart)
        self.chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        layout = QVBoxLayout(self); layout.setContentsMargins(0, 0, 0, 0); layout.addWidget(self.chart_view)

    def clear(self, message: str = "No verified transactions in this period"):
        self.chart.removeAllSeries(); self.chart.setTitle(f"{self.title} — {message}")

    def set_monthly(self, rows: list[dict], on_point=None):
        self.chart.removeAllSeries(); self.chart.setTitle(self.title)
        if not rows: return self.clear()
        sales = QLineSeries(); sales.setName("Sales")
        expenses = QLineSeries(); expenses.setName("Expenses")
        for index, row in enumerate(rows):
            sales.append(index, float(row.get("sales", 0))); expenses.append(index, float(row.get("expenses", 0)))
        if on_point: sales.clicked.connect(lambda point: on_point(rows[int(point.x())].get("source_ids", [])))
        self.chart.addSeries(sales); self.chart.addSeries(expenses)
        axis_x = QCategoryAxis(); [axis_x.append(row["month"], index) for index, row in enumerate(rows)]; axis_x.setRange(0, max(1, len(rows) - 1)); self.chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom); sales.attachAxis(axis_x); expenses.attachAxis(axis_x)
        axis_y = QValueAxis(); axis_y.setLabelFormat("%.0f"); self.chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft); sales.attachAxis(axis_y); expenses.attachAxis(axis_y)

    def set_categories(self, rows: list[dict], on_bar=None):
        self.chart.removeAllSeries(); self.chart.setTitle(self.title)
        if not rows: return self.clear()
        values = QBarSet("Amount")
        for row in rows: values.append(float(row.get("amount", 0)))
        series = QBarSeries(); series.append(values)
        if on_bar: series.clicked.connect(lambda _value, index: on_bar(rows[index].get("source_ids", [])))
        self.chart.addSeries(series)
        axis_x = QBarCategoryAxis(); axis_x.append([row.get("category", row.get("name", "")) for row in rows]); self.chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom); series.attachAxis(axis_x)
        axis_y = QValueAxis(); axis_y.setLabelFormat("%.0f"); self.chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft); series.attachAxis(axis_y)
