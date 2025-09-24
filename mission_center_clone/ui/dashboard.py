"""Dashboard view replicating Mission Center overview."""

from __future__ import annotations

from PySide6.QtWidgets import QGridLayout, QWidget

from mission_center_clone.models import (
    BatterySnapshot,
    CPUSnapshot,
    DiskSnapshot,
    FanSensorsSnapshot,
    GPUSnapshot,
    IOSnapshot,
    MemorySnapshot,
    NetworkSnapshot,
    PCIESnapshot,
    PowerSourcesSnapshot,
    SystemInfoSnapshot,
    TemperatureSensorsSnapshot,
)
from mission_center_clone.ui.widgets.resource_card import ResourceCard


def _format_bytes(num: float | int | None) -> str:
    if num is None or num < 0:
        return "--"
    value = float(num)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if value < 1024.0:
            return f"{value:.1f} {unit}"
        value /= 1024.0
    return f"{value:.1f} PB"


class DashboardView(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QGridLayout(self)
        layout.setSpacing(12)
        self._cards = {
            "cpu": ResourceCard("CPU"),
            "memory": ResourceCard("Memoria"),
            "gpu": ResourceCard("GPU"),
            "disk": ResourceCard("Almacenamiento"),
            "network": ResourceCard("Red"),
            "io": ResourceCard("IO"),
            "pcie": ResourceCard("PCIe"),
            "temperature": ResourceCard("Temperaturas"),
            "fans": ResourceCard("Ventiladores"),
            "battery": ResourceCard("Batería"),
            "power": ResourceCard("Energía"),
            "system": ResourceCard("Sistema"),
        }
        positions = [
            (0, 0, "cpu"),
            (0, 1, "memory"),
            (0, 2, "gpu"),
            (1, 0, "disk"),
            (1, 1, "network"),
            (1, 2, "io"),
            (2, 0, "pcie"),
            (2, 1, "temperature"),
            (2, 2, "fans"),
            (3, 0, "battery"),
            (3, 1, "power"),
            (3, 2, "system"),
        ]
        for row, col, key in positions:
            layout.addWidget(self._cards[key], row, col)
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 1)
        layout.setColumnStretch(2, 1)
        layout.setRowStretch(4, 1)

    def update_cpu(self, snapshot: CPUSnapshot) -> None:
        self._cards["cpu"].update_value(f"{snapshot.usage_percent:.1f}%")

    def update_memory(self, snapshot: MemorySnapshot) -> None:
        used = _format_bytes(snapshot.used_bytes)
        total = _format_bytes(snapshot.total_bytes)
        self._cards["memory"].update_value(f"{used} / {total} ({snapshot.percent:.1f}%)")

    def update_gpu(self, snapshots: list[GPUSnapshot]) -> None:
        if not snapshots:
            self._cards["gpu"].update_value("No detectado")
            return
        gpu = snapshots[0]
        util = gpu.utilization_percent if gpu.utilization_percent is not None else 0.0
        mem_total = _format_bytes(gpu.memory_total_bytes)
        mem_used = _format_bytes(gpu.memory_used_bytes)
        text = f"{gpu.name} — {util:.0f}%\n{mem_used} / {mem_total}"
        self._cards["gpu"].update_value(text)

    def update_disk(self, snapshot: DiskSnapshot) -> None:
        if not snapshot.devices:
            self._cards["disk"].update_value("Sin discos")
            return
        primary = snapshot.devices[0]
        used = _format_bytes(primary.used_bytes)
        total = _format_bytes(primary.total_bytes)
        self._cards["disk"].update_value(f"{used} / {total}")

    def update_network(self, snapshot: NetworkSnapshot) -> None:
        if not snapshot.interfaces:
            self._cards["network"].update_value("Sin interfaces")
            return
        iface = max(
            snapshot.interfaces,
            key=lambda iface: iface.sent_bytes_per_sec + iface.recv_bytes_per_sec,
        )
        up = _format_bytes(iface.sent_bytes_per_sec)
        down = _format_bytes(iface.recv_bytes_per_sec)
        self._cards["network"].update_value(f"↑ {up}/s\n↓ {down}/s")

    def update_io(self, snapshot: IOSnapshot) -> None:
        read = _format_bytes(snapshot.read_bytes_per_sec)
        write = _format_bytes(snapshot.write_bytes_per_sec)
        self._cards["io"].update_value(f"Lectura {read}/s\nEscritura {write}/s")

    def update_pcie(self, snapshot: PCIESnapshot) -> None:
        if not snapshot.devices:
            self._cards["pcie"].update_value("Sin datos")
            return
        active = sum(1 for device in snapshot.devices if device.link_speed_gtps)
        self._cards["pcie"].update_value(f"{active}/{len(snapshot.devices)} enlaces activos")

    def update_temperature(self, snapshot: TemperatureSensorsSnapshot) -> None:
        readings = [
            reading
            for group in snapshot.groups
            for reading in group.readings
            if reading.current_celsius is not None
        ]
        if not readings:
            self._cards["temperature"].update_value("Sin sensores")
            return
        max_reading = max(readings, key=lambda r: r.current_celsius or 0.0)
        avg = sum(r.current_celsius or 0.0 for r in readings) / len(readings)
        label = max_reading.label or max_reading.source
        self._cards["temperature"].update_value(
            f"Máx {max_reading.current_celsius:.1f}°C ({label})\nProm {avg:.1f}°C"
        )

    def update_fans(self, snapshot: FanSensorsSnapshot) -> None:
        readings = [r for r in snapshot.readings if r.speed_rpm is not None]
        if not readings:
            self._cards["fans"].update_value("Sin ventiladores")
            return
        max_rpm = max(readings, key=lambda r: r.speed_rpm or 0.0)
        avg_rpm = sum(r.speed_rpm or 0.0 for r in readings) / len(readings)
        label = max_rpm.label or max_rpm.source
        self._cards["fans"].update_value(
            f"Máx {max_rpm.speed_rpm:.0f} rpm ({label})\nProm {avg_rpm:.0f} rpm"
        )

    def update_battery(self, snapshot: BatterySnapshot) -> None:
        if snapshot.percent is None:
            self._cards["battery"].update_value("Sin batería")
            return
        status = "Enchufada" if snapshot.power_plugged else "Descargando"
        remaining = "--"
        if snapshot.secs_left:
            hours = int(snapshot.secs_left // 3600)
            minutes = int((snapshot.secs_left % 3600) // 60)
            remaining = f"{hours:02d}h{minutes:02d}m"
        self._cards["battery"].update_value(
            f"{snapshot.percent:.0f}% ({status})\nRestante {remaining}"
        )

    def update_power(self, snapshot: PowerSourcesSnapshot) -> None:
        if not snapshot.sources:
            self._cards["power"].update_value("Sin fuentes")
            return
        online = sum(1 for s in snapshot.sources if s.is_online)
        mains = next((s for s in snapshot.sources if s.name.lower().startswith("ac")), None)
        if mains and mains.power_watts:
            detail = f"AC {mains.power_watts:.1f} W"
        else:
            detail = f"{online}/{len(snapshot.sources)} activas"
        self._cards["power"].update_value(detail)

    def update_system(self, snapshot: SystemInfoSnapshot) -> None:
        os_text = " ".join(filter(None, [snapshot.os_name, snapshot.os_version])) or "--"
        uptime = "--"
        if snapshot.uptime_seconds is not None:
            hours = int(snapshot.uptime_seconds // 3600)
            uptime = f"{hours} h" if hours < 72 else f"{hours // 24} d"
        self._cards["system"].update_value(f"{os_text}\nUptime {uptime}")
