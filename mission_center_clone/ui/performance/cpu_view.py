"""CPU performance panel."""

from __future__ import annotations

from statistics import mean

from mission_center_clone.core import HISTORY
from mission_center_clone.models import CPUSnapshot
from mission_center_clone.ui.performance.base_view import PerformanceViewBase
from mission_center_clone.ui.widgets import LineHistoryChart


def _format_core_usage(snapshot: CPUSnapshot) -> str:
    if not snapshot.per_core:
        return "Sin datos por núcleo"
    core_lines = [
        f"Núcleo {core.core_id}: {core.usage_percent:.1f}%"
        for core in snapshot.per_core
    ]
    avg = mean(core.usage_percent for core in snapshot.per_core)
    return "\n".join([f"Promedio núcleos: {avg:.1f}%"] + core_lines)


class CPUPerformanceView(PerformanceViewBase):
    def __init__(self, parent: None | object = None) -> None:
        super().__init__("CPU", parent)
        self._chart = LineHistoryChart(
            ["Uso CPU %"],
            max_samples=HISTORY.short_window,
            y_range=(0.0, 100.0),
        )
        self.add_widget(self._chart)

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
