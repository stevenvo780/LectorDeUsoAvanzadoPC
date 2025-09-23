"""PCIe performance panel."""

from __future__ import annotations

from mission_center_clone.core import HISTORY
from mission_center_clone.models import PCIESnapshot
from mission_center_clone.ui.performance.base_view import PerformanceViewBase
from mission_center_clone.ui.widgets import LineHistoryChart


def _format_device(line: str | None) -> str:
    if not line:
        return "--"
    return line


class PCIEPerformanceView(PerformanceViewBase):
    def __init__(self, parent: None | object = None) -> None:
        super().__init__("PCIe", parent)
        self._chart = LineHistoryChart(
            ["Enlaces activos"],
            max_samples=HISTORY.medium_window,
        )
        self.add_widget(self._chart)

    def update_snapshot(self, snapshot: PCIESnapshot) -> None:
        if not snapshot.devices:
            self.update_summary("No se detectaron dispositivos PCIe")
            return
        lines = []
        active = 0
        for device in snapshot.devices:
            if device.link_speed_gtps:
                active += 1
            lines.append(
                f"{device.address} — { _format_device(device.vendor) }:{ _format_device(device.device) }"
            )
            lines.append(
                f"    Link {device.link_speed_gtps or '--'} GT/s x{device.link_width or '--'} (máx {device.max_link_speed_gtps or '--'} GT/s x{device.max_link_width or '--'})"
            )
        self.update_summary("\n".join(lines))
        self._chart.append_value(float(active))
