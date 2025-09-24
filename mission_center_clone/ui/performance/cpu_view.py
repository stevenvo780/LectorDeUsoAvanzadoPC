"""CPU performance panel."""

from __future__ import annotations

import math
from statistics import mean

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGridLayout, QLabel, QVBoxLayout, QWidget

from mission_center_clone.core import HISTORY
from mission_center_clone.models import CPUCoreMetric, CPUSnapshot
from mission_center_clone.ui.performance.base_view import PerformanceViewBase
from mission_center_clone.ui.widgets import LineHistoryChart


def _format_core_usage(snapshot: CPUSnapshot) -> str:
    if not snapshot.per_core:
        return "Sin datos por núcleo"
    avg = mean(core.usage_percent for core in snapshot.per_core)
    peak = max(snapshot.per_core, key=lambda core: core.usage_percent)
    low = min(snapshot.per_core, key=lambda core: core.usage_percent)
    return (
        f"Promedio núcleos: {avg:.1f}%\n"
        f"Pico: Núcleo {peak.core_id} — {peak.usage_percent:.1f}%\n"
        f"Mínimo: Núcleo {low.core_id} — {low.usage_percent:.1f}%"
    )


class CPUPerformanceView(PerformanceViewBase):
    def __init__(self, parent: None | object = None) -> None:
        super().__init__("CPU", parent)
        self._chart = LineHistoryChart(
            ["Uso CPU %"],
            max_samples=HISTORY.short_window,
            y_range=(0.0, 100.0),
        )
        self.add_widget(self._chart)

        self._core_container = QWidget()
        self._core_container.setObjectName("ResourceCard")
        container_layout = QVBoxLayout(self._core_container)
        container_layout.setContentsMargins(16, 16, 16, 16)
        container_layout.setSpacing(12)

        title_label = QLabel("Uso por núcleo")
        title_label.setProperty("class", "performance-subtitle")
        title_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        container_layout.addWidget(title_label)

        self._core_grid = QGridLayout()
        self._core_grid.setContentsMargins(0, 0, 0, 0)
        self._core_grid.setHorizontalSpacing(12)
        self._core_grid.setVerticalSpacing(12)
        container_layout.addLayout(self._core_grid)

        self._core_widgets: dict[int, QWidget] = {}
        self._core_labels: dict[int, QLabel] = {}
        self._core_charts: dict[int, LineHistoryChart] = {}

        self.add_widget(self._core_container)
        self._core_container.setVisible(False)

    def update_snapshot(self, snapshot: CPUSnapshot) -> None:
        freq = snapshot.frequency_current_mhz or 0.0
        max_freq = snapshot.frequency_max_mhz or 0.0
        load_avg = (
            f"Carga (1/5/15m): {snapshot.load_average[0]:.2f} / {snapshot.load_average[1]:.2f} / {snapshot.load_average[2]:.2f}"
            if snapshot.load_average
            else "Carga no disponible"
        )
        summary = (
            f"Uso actual: {snapshot.usage_percent:.1f}%\n"
            f"Frecuencia: {freq:.0f} MHz (máx {max_freq:.0f} MHz)\n"
            f"Lógicos: {snapshot.logical_cores} — Físicos: {snapshot.physical_cores or '--'}\n"
            f"Context Switches: {snapshot.context_switches or 0} — IRQ: {snapshot.interrupts or 0}\n"
            f"{load_avg}\n\n"
            f"{_format_core_usage(snapshot)}"
        )
        self.update_summary(summary)
        self._chart.append_value(snapshot.usage_percent)
        self._update_per_core_charts(snapshot)

    def _update_per_core_charts(self, snapshot: CPUSnapshot) -> None:
        if not snapshot.per_core:
            self._core_container.setVisible(False)
            return

        changed = self._ensure_core_widgets(snapshot.per_core)
        for metric in snapshot.per_core:
            chart = self._core_charts.get(metric.core_id)
            if chart:
                chart.append_value(metric.usage_percent)
            label = self._core_labels.get(metric.core_id)
            if label:
                label.setText(f"Núcleo {metric.core_id} — {metric.usage_percent:.1f}%")

        if changed:
            self._refresh_core_grid()

        self._core_container.setVisible(True)

    def _ensure_core_widgets(self, per_core: list[CPUCoreMetric]) -> bool:
        existing_ids = set(self._core_charts.keys())
        incoming_ids = {metric.core_id for metric in per_core}
        changed = False

        for core_id in existing_ids - incoming_ids:
            widget = self._core_widgets.pop(core_id, None)
            if widget is not None:
                widget.setParent(None)
            self._core_charts.pop(core_id, None)
            self._core_labels.pop(core_id, None)
            changed = True

        for metric in per_core:
            core_id = metric.core_id
            if core_id in self._core_charts:
                continue
            container = QWidget()
            container.setObjectName("ResourceCard")
            layout = QVBoxLayout(container)
            layout.setContentsMargins(12, 12, 12, 12)
            layout.setSpacing(8)

            label = QLabel(f"Núcleo {core_id}")
            label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            layout.addWidget(label)

            chart = LineHistoryChart(
                [f"Núcleo {core_id}"],
                max_samples=HISTORY.short_window,
                y_range=(0.0, 100.0),
                show_axes=False,
                minimum_height=140,
                x_axis_title=None,
            )
            layout.addWidget(chart)

            self._core_widgets[core_id] = container
            self._core_labels[core_id] = label
            self._core_charts[core_id] = chart
            changed = True

        return changed

    def _refresh_core_grid(self) -> None:
        core_ids = sorted(self._core_charts.keys())
        for i in reversed(range(self._core_grid.count())):
            self._core_grid.takeAt(i)

        columns = self._calculate_columns(len(core_ids))
        for column in range(columns):
            self._core_grid.setColumnStretch(column, 1)
        for index, core_id in enumerate(core_ids):
            row = index // columns
            column = index % columns
            self._core_grid.addWidget(self._core_widgets[core_id], row, column)

    @staticmethod
    def _calculate_columns(core_count: int) -> int:
        if core_count <= 1:
            return 1
        columns = max(2, math.ceil(math.sqrt(core_count)))
        return min(columns, 6)
