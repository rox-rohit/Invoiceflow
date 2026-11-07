from __future__ import annotations

from PySide6.QtCharts import (
    QBarCategoryAxis,
    QBarSeries,
    QBarSet,
    QChart,
    QChartView,
    QLineSeries,
    QPieSeries,
    QValueAxis,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QPainter
from PySide6.QtWidgets import QSizePolicy, QVBoxLayout, QWidget


class FinancialChart(QWidget):
    """Data-backed QtCharts card with explicit axes and intentional empty states."""

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.title = title
        self.setMinimumHeight(260)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.chart = QChart()
        self.chart.setTitle(title)
        # Financial charts should show their complete data immediately after a
        # refresh; an in-progress bar animation makes screenshots and quick
        # period changes appear to contain incomplete values.
        self.chart.setAnimationOptions(QChart.AnimationOption.NoAnimation)
        self.chart.legend().setVisible(True)
        self.chart_view = QChartView(self.chart)
        self.chart_view.setMinimumHeight(240)
        self.chart_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.chart_view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.apply_theme("light")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.chart_view)

    def apply_theme(self, preference: str) -> None:
        self._theme_preference = preference
        dark = preference == "dark"
        background = QColor("#202B3D" if dark else "#FFFFFF")
        plot = QColor("#202B3D" if dark else "#FFFFFF")
        text = QColor("#D7E2EE" if dark else "#172B4D")
        grid = QColor("#3A475B" if dark else "#E2E8F0")
        self.chart.setBackgroundBrush(QBrush(background))
        self.chart.setPlotAreaBackgroundBrush(QBrush(plot))
        self.chart.setPlotAreaBackgroundVisible(True)
        self.chart.setTitleBrush(QBrush(text))
        self.chart.legend().setLabelColor(text)
        for axis in self.chart.axes():
            axis.setLabelsColor(text)
            axis.setTitleBrush(QBrush(text))
            axis.setGridLineColor(grid)

    def _reset(self, title: str | None = None):
        self.chart.removeAllSeries()
        for axis in list(self.chart.axes()):
            self.chart.removeAxis(axis)
        self.chart.setTitle(title or self.title)

    def clear(self, message: str = "No verified transactions in this period"):
        self._reset(f"{self.title} — {message}")

    @staticmethod
    def _axis_max(values: list[float]) -> float:
        maximum = max([abs(value) for value in values] + [1.0])
        return maximum * 1.15

    def set_grouped_bars(self, rows: list[dict], series: tuple[tuple[str, str], ...], on_bar=None):
        self._reset()
        if not rows:
            return self.clear()
        categories = [row.get("label", row.get("month", "")) for row in rows]
        chart_series = []
        all_values = []
        for key, name in series:
            values = QBarSet(name)
            values.setColor({"sales": "#2A9D8F", "purchases": "#4E8B78", "expenses": "#C08457", "collections": "#5D946A", "payments": "#7568A8", "budget": "#64748B", "actual": "#2A9D8F", "remaining": "#5D946A"}.get(key, "#64748B"))
            for row in rows:
                number = float(row.get(key, 0))
                values.append(number)
                all_values.append(number)
            if on_bar:
                values.clicked.connect(lambda index, data_key=key: on_bar(rows[index], data_key, True))
            chart_series.append(values)
        grouped = QBarSeries()
        for values in chart_series:
            grouped.append(values)
        self.chart.addSeries(grouped)
        axis_x = QBarCategoryAxis()
        axis_x.append(categories)
        axis_y = QValueAxis()
        maximum = self._axis_max(all_values)
        minimum = -maximum if min(all_values or [0]) < 0 else 0
        axis_y.setRange(minimum, maximum)
        axis_y.setLabelFormat("%.0f")
        self.chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        self.chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
        grouped.attachAxis(axis_x)
        grouped.attachAxis(axis_y)
        self.apply_theme(self._theme_preference)

    def set_revenue_expenses(self, rows: list[dict], on_bar=None):
        self.set_grouped_bars(
            rows,
            (("sales", "Revenue"), ("purchases", "Purchases"), ("expenses", "Operating expenses")),
            on_bar,
        )

    def set_cash_movement(self, rows: list[dict], on_bar=None):
        self.set_grouped_bars(
            rows,
            (("collections", "Collections"), ("payments", "Payments")),
            on_bar,
        )

    def set_budget_utilization(self, rows: list[dict], on_bar=None):
        self.set_grouped_bars(
            rows,
            (("budget", "Budgeted"), ("actual", "Actual spending"), ("remaining", "Remaining")),
            on_bar,
        )

    def set_line(self, rows: list[dict], value_key: str, name: str, on_point=None):
        self._reset()
        if not rows:
            return self.clear()
        line = QLineSeries()
        line.setName(name)
        line.setColor("#2A9D8F")
        values = []
        for index, row in enumerate(rows):
            number = float(row.get(value_key, 0))
            line.append(index, number)
            values.append(number)
        if on_point:
            line.hovered.connect(lambda point, state: on_point(rows[int(point.x())], state))
        self.chart.addSeries(line)
        axis_x = QBarCategoryAxis()
        axis_x.append([row.get("label", "") for row in rows])
        axis_y = QValueAxis()
        axis_y.setRange(0, self._axis_max(values))
        axis_y.setLabelFormat("%.0f")
        self.chart.addAxis(axis_x, Qt.AlignmentFlag.AlignBottom)
        self.chart.addAxis(axis_y, Qt.AlignmentFlag.AlignLeft)
        line.attachAxis(axis_x)
        line.attachAxis(axis_y)
        self.apply_theme(self._theme_preference)

    def set_categories(self, rows: list[dict], on_bar=None):
        self._reset()
        if not rows:
            return self.clear("No operating expenses in this period")
        series = QPieSeries()
        total = sum(float(row.get("amount", 0)) for row in rows)
        for row in rows:
            value = float(row.get("amount", 0))
            category = str(row.get("category", "Uncategorized"))
            legend_label = f"{category}  {value:,.2f} ({value / total:.1%})" if total else f"{category}  0.0%"
            slice_item = series.append(legend_label, value)
            slice_item.setLabelVisible(False)
            slice_item.hovered.connect(lambda state, item=slice_item: item.setExploded(state))
            if on_bar:
                slice_item.clicked.connect(
                    lambda item=slice_item, data=row: on_bar(
                        data.get("source_ids", []), data.get("category", "Uncategorized"), data.get("amount", 0)
                    )
                )
        self.chart.addSeries(series)
        self.chart.legend().setVisible(True)
        self.apply_theme(self._theme_preference)

    # Compatibility with the 2.4.0/2.4.1 callers.
    def set_monthly(self, rows: list[dict], on_point=None):
        self.set_revenue_expenses(rows, on_point)
