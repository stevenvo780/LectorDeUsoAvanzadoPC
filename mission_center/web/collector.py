"""Background data collection for the Mission Center web UI."""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import asdict
import threading
import time
from typing import Any, Callable, Deque

from mission_center.core import HISTORY
from mission_center.data import (
    collect_battery_snapshot,
    collect_cpu_snapshot,
    collect_disk_snapshot,
    collect_fan_sensors,
    collect_gpu_snapshot,
    collect_io_snapshot,
    collect_memory_snapshot,
    collect_network_snapshot,
    collect_pcie_snapshot,
    collect_power_sources_snapshot,
    collect_process_snapshot,
    collect_system_info,
    collect_temperature_sensors,
)
from mission_center.models import (
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
    ProcessSnapshot,
    SystemInfoSnapshot,
    TemperatureSensorsSnapshot,
)


_PRIMITIVE_TYPES = (int, float, str, bool)


def _snapshot_to_dict(snapshot: Any) -> Any:
    """Convert dataclass snapshots into plain serialisable dictionaries."""

    if snapshot is None:
        return None
    if isinstance(snapshot, _PRIMITIVE_TYPES):
        return snapshot
    if hasattr(snapshot, "to_dict"):
        return snapshot.to_dict()
    if hasattr(snapshot, "_asdict"):
        return snapshot._asdict()
    if hasattr(snapshot, "__dataclass_fields__"):
        return asdict(snapshot)
    if isinstance(snapshot, dict):
        return {key: _snapshot_to_dict(value) for key, value in snapshot.items()}
    if isinstance(snapshot, (list, tuple, set)):
        return [_snapshot_to_dict(item) for item in snapshot]
    return snapshot


class DataCollector:
    """Polls the data providers and keeps rolling histories for the web UI."""

    def __init__(self, interval: float = 1.0) -> None:
        self._interval = interval
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._lock = threading.RLock()

        history_size = HISTORY.short_window
        medium_history = HISTORY.medium_window

        self.cpu_history: Deque[dict[str, Any]] = deque(maxlen=history_size)
        self.memory_history: Deque[dict[str, Any]] = deque(maxlen=history_size)
        self.disk_history: Deque[dict[str, Any]] = deque(maxlen=history_size)
        self.network_history: Deque[dict[str, Any]] = deque(maxlen=history_size)
        self.io_history: Deque[dict[str, Any]] = deque(maxlen=history_size)
        self.gpu_history: Deque[dict[str, Any]] = deque(maxlen=medium_history)
        self.temperature_history: Deque[dict[str, Any]] = deque(maxlen=medium_history)
        self.fan_history: Deque[dict[str, Any]] = deque(maxlen=medium_history)

        self.cpu_core_history: dict[int, Deque[dict[str, Any]]] = defaultdict(
            lambda: deque(maxlen=history_size)
        )

        self.current_data: dict[str, Any] = {}

        self._providers: dict[str, Callable[[], Any]] = {
            "cpu": collect_cpu_snapshot,
            "memory": collect_memory_snapshot,
            "disk": collect_disk_snapshot,
            "network": collect_network_snapshot,
            "io": collect_io_snapshot,
            "gpu": collect_gpu_snapshot,
            "pcie": collect_pcie_snapshot,
            "processes": collect_process_snapshot,
            "temperature": collect_temperature_sensors,
            "fans": collect_fan_sensors,
            "battery": collect_battery_snapshot,
            "power": collect_power_sources_snapshot,
            "system": collect_system_info,
        }

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="DataCollector", daemon=True)
        self._thread.start()

    def stop(self, timeout: float | None = None) -> None:
        self._stop.set()
        thread = self._thread
        if thread and thread.is_alive():
            thread.join(timeout=timeout)
        self._thread = None

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return _snapshot_to_dict(self.current_data)

    def history(self) -> dict[str, Any]:
        with self._lock:
            return {
                "cpu": list(self.cpu_history),
                "cpu_cores": {core: list(history) for core, history in self.cpu_core_history.items()},
                "memory": list(self.memory_history),
                "disk": list(self.disk_history),
                "network": list(self.network_history),
                "io": list(self.io_history),
                "gpu": list(self.gpu_history),
                "temperature": list(self.temperature_history),
                "fans": list(self.fan_history),
            }

    def _run(self) -> None:
        while not self._stop.is_set():
            start_time = time.perf_counter()
            try:
                self._collect_all()
            except Exception:  # pragma: no cover - defensive guard for runtime collectors
                # We keep the collector alive even if a provider fails.
                pass
            elapsed = time.perf_counter() - start_time
            delay = max(0.1, self._interval - elapsed)
            self._stop.wait(delay)

    def _collect_all(self) -> None:
        timestamp = time.time()

        cpu_snapshot = self._safe_call("cpu", collect_cpu_snapshot, CPUSnapshot)
        memory_snapshot = self._safe_call("memory", collect_memory_snapshot, MemorySnapshot)
        disk_snapshot = self._safe_call("disk", collect_disk_snapshot, DiskSnapshot)
        network_snapshot = self._safe_call("network", collect_network_snapshot, NetworkSnapshot)
        io_snapshot = self._safe_call("io", collect_io_snapshot, IOSnapshot)
        gpu_snapshot = self._safe_call("gpu", collect_gpu_snapshot, list)
        pcie_snapshot = self._safe_call("pcie", collect_pcie_snapshot, PCIESnapshot)
        process_snapshot = self._safe_call("processes", collect_process_snapshot, ProcessSnapshot)
        temperature_snapshot = self._safe_call("temperature", collect_temperature_sensors, TemperatureSensorsSnapshot)
        fan_snapshot = self._safe_call("fans", collect_fan_sensors, FanSensorsSnapshot)
        battery_snapshot = self._safe_call("battery", collect_battery_snapshot, BatterySnapshot)
        power_snapshot = self._safe_call("power", collect_power_sources_snapshot, PowerSourcesSnapshot)
        system_snapshot = self._safe_call("system", collect_system_info, SystemInfoSnapshot)

        with self._lock:
            if cpu_snapshot:
                self.cpu_history.append({
                    "time": timestamp,
                    "usage": cpu_snapshot.usage_percent,
                    "frequency": cpu_snapshot.frequency_current_mhz or 0.0,
                })
                for core in cpu_snapshot.per_core:
                    self.cpu_core_history[core.core_id].append({
                        "time": timestamp,
                        "usage": core.usage_percent,
                        "frequency": core.frequency_mhz or 0.0,
                    })

            if memory_snapshot:
                self.memory_history.append({
                    "time": timestamp,
                    "usage": memory_snapshot.percent,
                    "used": memory_snapshot.used_bytes,
                    "available": memory_snapshot.available_bytes,
                    "swap_usage": memory_snapshot.swap_percent,
                    "swap_used": memory_snapshot.swap_used_bytes,
                })

            if disk_snapshot:
                total_read = sum(device.read_bytes_per_sec or 0 for device in disk_snapshot.devices)
                total_write = sum(device.write_bytes_per_sec or 0 for device in disk_snapshot.devices)
                self.disk_history.append({
                    "time": timestamp,
                    "read": total_read,
                    "write": total_write,
                })

            if network_snapshot:
                total_sent = sum(interface.sent_bytes_per_sec for interface in network_snapshot.interfaces)
                total_recv = sum(interface.recv_bytes_per_sec for interface in network_snapshot.interfaces)
                self.network_history.append({
                    "time": timestamp,
                    "sent": total_sent,
                    "recv": total_recv,
                })

            if io_snapshot:
                self.io_history.append({
                    "time": timestamp,
                    "read": io_snapshot.read_bytes_per_sec,
                    "write": io_snapshot.write_bytes_per_sec,
                })

            if gpu_snapshot:
                self.gpu_history.append({
                    "time": timestamp,
                    "gpus": [_snapshot_to_dict(gpu) for gpu in gpu_snapshot],
                })

            if temperature_snapshot:
                flat_readings = [
                    {
                        "source": reading.source,
                        "label": reading.label,
                        "current": reading.current_celsius,
                    }
                    for group in temperature_snapshot.groups
                    for reading in group.readings
                ]
                self.temperature_history.append({
                    "time": timestamp,
                    "readings": flat_readings,
                })

            if fan_snapshot:
                self.fan_history.append({
                    "time": timestamp,
                    "readings": [
                        {
                            "source": reading.source,
                            "label": reading.label,
                            "speed": reading.speed_rpm,
                        }
                        for reading in fan_snapshot.readings
                    ],
                })

            self.current_data = {
                "timestamp": timestamp,
                "cpu": _snapshot_to_dict(cpu_snapshot),
                "memory": _snapshot_to_dict(memory_snapshot),
                "disk": _snapshot_to_dict(disk_snapshot),
                "network": _snapshot_to_dict(network_snapshot),
                "io": _snapshot_to_dict(io_snapshot),
                "gpu": _snapshot_to_dict(gpu_snapshot),
                "pcie": _snapshot_to_dict(pcie_snapshot),
                "processes": _snapshot_to_dict(process_snapshot),
                "temperature": _snapshot_to_dict(temperature_snapshot),
                "fans": _snapshot_to_dict(fan_snapshot),
                "battery": _snapshot_to_dict(battery_snapshot),
                "power": _snapshot_to_dict(power_snapshot),
                "system": _snapshot_to_dict(system_snapshot),
            }

    def _safe_call(self, key: str, fn: Callable[[], Any], expected_type: type[Any] | tuple[type[Any], ...]) -> Any:
        try:
            result = fn()
        except Exception:
            return None
        if expected_type is list and isinstance(result, list):
            return result
        if isinstance(result, expected_type):
            return result
        return None


collector = DataCollector()
"""Module-level collector instance used by the web server."""
