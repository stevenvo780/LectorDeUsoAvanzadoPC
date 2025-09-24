"""System information view."""

from __future__ import annotations

import datetime as dt

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFormLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from mission_center_clone.models import SystemInfoSnapshot


def _format_bytes(value: int | None) -> str:
    if value is None or value < 0:
        return "--"
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    v = float(value)
    for unit in units:
        if v < 1024.0:
            return f"{v:.1f} {unit}"
        v /= 1024.0
    return f"{v:.1f} EB"


def _format_duration(seconds: float | None) -> str:
    if seconds is None:
        return "--"
    total_seconds = int(seconds)
    days, rem = divmod(total_seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, _ = divmod(rem, 60)
    parts = []
    if days:
        parts.append(f"{days}d")
    parts.append(f"{hours:02d}h")
    parts.append(f"{minutes:02d}m")
    return " ".join(parts)


class SystemInfoView(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        self._form = QFormLayout()
        self._form.setLabelAlignment(Qt.AlignRight)

        self._hostname = QLabel("--")
        self._os = QLabel("--")
        self._kernel = QLabel("--")
        self._arch = QLabel("--")
        self._cpu = QLabel("--")
        self._memory = QLabel("--")
        self._cores = QLabel("--")
        self._uptime = QLabel("--")
        self._boot_time = QLabel("--")
        self._bios = QLabel("--")
        self._board = QLabel("--")
        self._machine = QLabel("--")
        self._virtualization = QLabel("--")

        self._form.addRow("Host", self._hostname)
        self._form.addRow("Sistema", self._os)
        self._form.addRow("Kernel", self._kernel)
        self._form.addRow("Arquitectura", self._arch)
        self._form.addRow("CPU", self._cpu)
        self._form.addRow("Memoria", self._memory)
        self._form.addRow("Núcleos", self._cores)
        self._form.addRow("Uptime", self._uptime)
        self._form.addRow("Arranque", self._boot_time)
        self._form.addRow("BIOS", self._bios)
        self._form.addRow("Baseboard", self._board)
        self._form.addRow("Equipo", self._machine)
        self._form.addRow("Virtualización", self._virtualization)

        layout.addLayout(self._form)

        self._gpu_label = QLabel("GPUs detectadas")
        self._gpu_list = QListWidget()
        self._gpu_list.setSelectionMode(QAbstractItemView.NoSelection)
        self._gpu_list.setUniformItemSizes(True)
        self._gpu_list.setMinimumHeight(120)

        layout.addWidget(self._gpu_label)
        layout.addWidget(self._gpu_list, 1)

    def update_snapshot(self, snapshot: SystemInfoSnapshot) -> None:
        self._hostname.setText(snapshot.hostname or "--")
        os_text = " ".join(filter(None, [snapshot.os_name, snapshot.os_version]))
        self._os.setText(os_text or "--")
        kernel = snapshot.kernel_version or "--"
        if snapshot.os_name and snapshot.kernel_version:
            kernel = f"{snapshot.os_name} {snapshot.kernel_version}"
        self._kernel.setText(kernel)
        self._arch.setText(snapshot.architecture or "--")
        cpu_parts = [snapshot.cpu_model or "--"]
        if snapshot.logical_cores:
            cpu_parts.append(f"{snapshot.logical_cores} lógicos")
        if snapshot.physical_cores:
            cpu_parts.append(f"{snapshot.physical_cores} físicos")
        self._cpu.setText(" | ".join(cpu_parts))
        self._memory.setText(_format_bytes(snapshot.total_memory_bytes))
        if snapshot.physical_cores is not None or snapshot.logical_cores is not None:
            self._cores.setText(
                f"Físicos: {snapshot.physical_cores or '--'} | Lógicos: {snapshot.logical_cores or '--'}"
            )
        else:
            self._cores.setText("--")
        self._uptime.setText(_format_duration(snapshot.uptime_seconds))
        if snapshot.boot_time:
            dt_boot = dt.datetime.fromtimestamp(snapshot.boot_time)
            self._boot_time.setText(dt_boot.strftime("%Y-%m-%d %H:%M"))
        else:
            self._boot_time.setText("--")
        bios_parts = [snapshot.bios_vendor or "", snapshot.bios_version or "", snapshot.bios_date or ""]
        bios_text = " | ".join([part for part in bios_parts if part])
        self._bios.setText(bios_text or "--")
        board_parts = [snapshot.motherboard or "", snapshot.system_manufacturer or ""]
        self._board.setText(" | ".join([part for part in board_parts if part]) or "--")
        machine_parts = [snapshot.system_manufacturer or "", snapshot.system_model or "", snapshot.chassis_type or ""]
        self._machine.setText(" | ".join([part for part in machine_parts if part]) or "--")
        self._virtualization.setText(snapshot.virtualization or "--")

        self._gpu_list.clear()
        if snapshot.gpu_devices:
            for device in snapshot.gpu_devices:
                item = QListWidgetItem(device)
                self._gpu_list.addItem(item)
        else:
            self._gpu_list.addItem(QListWidgetItem("Sin GPU dedicada detectada"))
