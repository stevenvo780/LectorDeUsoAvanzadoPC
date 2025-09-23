"""GPU performance panel."""

from __future__ import annotations

from mission_center_clone.core import HISTORY
from mission_center_clone.models import GPUSnapshot
from mission_center_clone.ui.performance.base_view import PerformanceViewBase
from mission_center_clone.ui.widgets import LineHistoryChart


def _format_bytes(num: int | None) -> str:
    if num is None:
        return "--"
    value = float(num)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if value < 1024.0:
            return f"{value:.1f} {unit}"
        value /= 1024.0
    return f"{value:.1f} PB"


class GPUPerformanceView(PerformanceViewBase):
    def __init__(self, parent: None | object = None) -> None:
        super().__init__("GPU", parent)
        self._chart = LineHistoryChart(
            ["Uso GPU %"],
            max_samples=HISTORY.short_window,
            y_range=(0.0, 100.0),
        )
        self.add_widget(self._chart)

    def update_snapshots(self, snapshots: list[GPUSnapshot]) -> None:
        if not snapshots:
            self.update_summary("GPU no detectada o sin soporte")
            return
        gpu = snapshots[0]
        utilization = float(gpu.utilization_percent or 0.0)
        summary = (
            f"{gpu.name} ({gpu.vendor})\n"
            f"Uso: {utilization:.1f}%\n"
            f"Memoria: {_format_bytes(gpu.memory_used_bytes)} / {_format_bytes(gpu.memory_total_bytes)}\n"
            f"Temperatura: {gpu.temperature_celsius or 0:.1f}°C\n"
            f"Extra: {gpu.extra}"
        )
        self.update_summary(summary)
        self._chart.append_value(utilization)
