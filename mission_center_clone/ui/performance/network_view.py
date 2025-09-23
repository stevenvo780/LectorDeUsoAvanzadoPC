"""Network performance panel."""

from __future__ import annotations

from mission_center_clone.core import HISTORY
from mission_center_clone.models import NetworkSnapshot
from mission_center_clone.ui.performance.base_view import PerformanceViewBase
from mission_center_clone.ui.widgets import LineHistoryChart


def _format_bytes(num: float) -> str:
    value = float(num)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if value < 1024.0:
            return f"{value:.1f} {unit}"
        value /= 1024.0
    return f"{value:.1f} PB"


class NetworkPerformanceView(PerformanceViewBase):
    def __init__(self, parent: None | object = None) -> None:
        super().__init__("Red", parent)
        self._chart = LineHistoryChart(
            ["Subida B/s", "Bajada B/s"],
            max_samples=HISTORY.short_window,
        )
        self.add_widget(self._chart)

    def update_snapshot(self, snapshot: NetworkSnapshot) -> None:
        if not snapshot.interfaces:
            self.update_summary("Sin interfaces de red")
            return
        lines = []
        total_up = 0.0
        total_down = 0.0
        for iface in snapshot.interfaces:
            up = float(iface.sent_bytes_per_sec)
            down = float(iface.recv_bytes_per_sec)
            total_up += up
            total_down += down
            lines.append(
                f"{iface.name} ({'UP' if iface.is_up else 'DOWN'}) {iface.address or ''}"
            )
            lines.append(
                f"    ↑ {_format_bytes(up)}/s — ↓ {_format_bytes(down)}/s"
            )
        self.update_summary("\n".join(lines))
        self._chart.append_values({"Subida B/s": total_up, "Bajada B/s": total_down})
