"""Memory performance panel."""

from __future__ import annotations

from mission_center_clone.core import HISTORY
from mission_center_clone.models import MemorySnapshot
from mission_center_clone.ui.performance.base_view import PerformanceViewBase
from mission_center_clone.ui.widgets import LineHistoryChart


def _format_bytes(num: int) -> str:
    value = float(num)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if value < 1024.0:
            return f"{value:.1f} {unit}"
        value /= 1024.0
    return f"{value:.1f} PB"


class MemoryPerformanceView(PerformanceViewBase):
    def __init__(self, parent: None | object = None) -> None:
        super().__init__("Memoria", parent)
        self._chart = LineHistoryChart(
            ["Uso RAM %"],
            max_samples=HISTORY.short_window,
            y_range=(0.0, 100.0),
        )
        self.add_widget(self._chart)

    def update_snapshot(self, snapshot: MemorySnapshot) -> None:
        summary = (
            f"Uso: {snapshot.percent:.1f}%\n"
            f"Utilizada: {_format_bytes(snapshot.used_bytes)}\n"
            f"Disponible: {_format_bytes(snapshot.available_bytes)}\n"
            f"Total: {_format_bytes(snapshot.total_bytes)}\n\n"
            f"Swap: {_format_bytes(snapshot.swap_used_bytes)} / {_format_bytes(snapshot.swap_total_bytes)} ({snapshot.swap_percent:.1f}%)"
        )
        self.update_summary(summary)
        self._chart.append_value(snapshot.percent)
