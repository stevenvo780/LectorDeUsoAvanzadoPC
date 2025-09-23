"""Disk performance panel."""

from __future__ import annotations

from mission_center_clone.core import HISTORY
from mission_center_clone.models import DiskSnapshot
from mission_center_clone.ui.performance.base_view import PerformanceViewBase
from mission_center_clone.ui.widgets import LineHistoryChart


def _format_bytes(num: float | int | None) -> str:
    if num is None:
        return "--"
    value = float(num)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if value < 1024.0:
            return f"{value:.1f} {unit}"
        value /= 1024.0
    return f"{value:.1f} PB"


class DiskPerformanceView(PerformanceViewBase):
    def __init__(self, parent: None | object = None) -> None:
        super().__init__("Almacenamiento", parent)
        self._chart = LineHistoryChart(
            ["Lectura B/s", "Escritura B/s"],
            max_samples=HISTORY.short_window,
        )
        self.add_widget(self._chart)

    def update_snapshot(self, snapshot: DiskSnapshot) -> None:
        if not snapshot.devices:
            self.update_summary("Sin discos detectados")
            return
        lines = []
        total_read = 0.0
        total_write = 0.0
        for device in snapshot.devices:
            read_rate = float(device.read_bytes_per_sec or 0.0)
            write_rate = float(device.write_bytes_per_sec or 0.0)
            total_read += read_rate
            total_write += write_rate
            lines.append(
                f"{device.name} ({device.mountpoint or 'sin montar'}) — {_format_bytes(device.used_bytes)} / {_format_bytes(device.total_bytes)}"
            )
            lines.append(
                f"    Lectura: {_format_bytes(device.read_bytes_per_sec)}/s, Escritura: {_format_bytes(device.write_bytes_per_sec)}/s"
            )
        self.update_summary("\n".join(lines))
        self._chart.append_values({"Lectura B/s": total_read, "Escritura B/s": total_write})
