"""IO performance panel."""

from __future__ import annotations

from mission_center_clone.core import HISTORY
from mission_center_clone.models import IOSnapshot
from mission_center_clone.ui.performance.base_view import PerformanceViewBase
from mission_center_clone.ui.widgets import LineHistoryChart


def _format_bytes(num: float) -> str:
    value = float(num)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if value < 1024.0:
            return f"{value:.1f} {unit}"
        value /= 1024.0
    return f"{value:.1f} PB"


class IOPerformanceView(PerformanceViewBase):
    def __init__(self, parent: None | object = None) -> None:
        super().__init__("IO", parent)
        self._chart = LineHistoryChart(
            ["Lectura B/s", "Escritura B/s"],
            max_samples=HISTORY.short_window,
        )
        self.add_widget(self._chart)

    def update_snapshot(self, snapshot: IOSnapshot) -> None:
        summary = (
            f"Lectura: {_format_bytes(snapshot.read_bytes_per_sec)}/s\n"
            f"Escritura: {_format_bytes(snapshot.write_bytes_per_sec)}/s\n"
            f"Óperaciones: {snapshot.read_count_delta} / {snapshot.write_count_delta}"
        )
        self.update_summary(summary)
        self._chart.append_values(
            {
                "Lectura B/s": float(snapshot.read_bytes_per_sec),
                "Escritura B/s": float(snapshot.write_bytes_per_sec),
            }
        )
