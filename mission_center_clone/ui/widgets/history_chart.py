"""Reusable line chart with a rolling history window."""

from __future__ import annotations

from collections import deque
from typing import Iterable, Mapping

from PySide6.QtCharts import QChart, QChartView, QLineSeries, QValueAxis
from PySide6.QtCore import QMargins, QPointF, Qt
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QWidget

_DEFAULT_COLORS = [
    "#22d3ee",  # cyan
    "#f97316",  # orange
    "#22c55e",  # green
    "#a855f7",  # purple
]


class LineHistoryChart(QChartView):
    """Minimal chart for plotting one or more series over a fixed window."""

    def __init__(
        self,
        series_names: Iterable[str],
        *,
        max_samples: int = 120,
        y_range: tuple[float | None, float | None] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        self._series_names = list(series_names)
        if not self._series_names:
            raise ValueError("At least one series name is required")
        super().__init__(parent)
        self._max_samples = max_samples
        self._y_range = y_range
        self._series: dict[str, QLineSeries] = {}
        self._data: dict[str, deque[tuple[int, float]]] = {
            name: deque(maxlen=max_samples) for name in self._series_names
        }
        self._sample_index = 0

        chart = QChart()
        chart.legend().setVisible(len(self._series_names) > 1)
        chart.setBackgroundRoundness(12)
        chart.setMargins(QMargins(12, 12, 12, 12))
        chart.layout().setContentsMargins(0, 0, 0, 0)

        self._axis_x = QValueAxis()
        self._axis_x.setTickCount(6)
        self._axis_x.setLabelFormat("%d")
        # Usamos índice de muestras; si se quiere tiempo real, migrar a timestamps
        self._axis_x.setTitleText("Muestras recientes")
        chart.addAxis(self._axis_x, Qt.AlignmentFlag.AlignBottom)

        self._axis_y = QValueAxis()
        self._axis_y.setTickCount(6)
        self._axis_y.setLabelFormat("%.0f")
        chart.addAxis(self._axis_y, Qt.AlignmentFlag.AlignLeft)

        for index, name in enumerate(self._series_names):
            series = QLineSeries(name=name)
            color = _DEFAULT_COLORS[index % len(_DEFAULT_COLORS)]
            series.setColor(color)
            chart.addSeries(series)
            series.attachAxis(self._axis_x)
            series.attachAxis(self._axis_y)
            self._series[name] = series

        self.setChart(chart)
        self.setRenderHint(QPainter.Antialiasing)
        self.setMinimumHeight(260)

    def append_value(self, value: float) -> None:
        """Shorthand for single-series charts."""

        if len(self._series_names) != 1:
            raise ValueError("append_value only available for single-series charts")
        self.append_values({self._series_names[0]: value})

    def append_values(self, values: Mapping[str, float]) -> None:
        self._sample_index += 1
        for name, value in values.items():
            if name in self._data:
                self._data[name].append((self._sample_index, float(value)))
        self._rebuild()

    def _rebuild(self) -> None:
        sample_count = max((len(buf) for buf in self._data.values()), default=0)
        if sample_count == 0:
            return

        x_end = self._sample_index
        x_start = max(0, x_end - self._max_samples)
        self._axis_x.setRange(x_start, max(x_start + 1, x_end))

        all_values = [value for buf in self._data.values() for _, value in buf]
        if not all_values:
            return
        if self._y_range is None:
            y_min = min(all_values)
            y_max = max(all_values)
            if y_min == y_max:
                y_max = y_min + 1.0
            padding = (y_max - y_min) * 0.1 or 0.5
            self._axis_y.setRange(y_min - padding, y_max + padding)
            self._axis_y.setLabelFormat("%.1f")
        else:
            ymin, ymax = self._y_range
            if ymin is not None and ymax is not None and ymin == ymax:
                ymax = ymin + 1.0
            if ymin is None:
                ymin = min(all_values)
            if ymax is None:
                ymax = max(all_values)
            self._axis_y.setRange(ymin, ymax)

        for name, series in self._series.items():
            points = [QPointF(x, y) for x, y in self._data[name]]
            series.replace(points)
