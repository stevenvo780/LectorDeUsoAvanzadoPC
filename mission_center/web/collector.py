"""Background data collection for the Mission Center web UI."""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import asdict
import logging
import os
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
logger = logging.getLogger(__name__)


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

        # Estado de permisos del sistema (se refresca de forma diferida)
        self.permission_status: dict[str, Any] = {
            "permission_level": "pending",
            "warnings": ["Determinando permisos del sistema"],
            "has_root": False,
            "accessible_paths": {},
            "access_percentage": 0,
            "is_container": False,
        }
        self._permission_refresh_interval = 180.0
        self._last_permission_refresh = 0.0
        self._permissions_thread: threading.Thread | None = None

        self._diagnostics: dict[str, Any] = {
            "last_run_started": None,
            "last_run_duration": 0.0,
            "last_success_at": None,
            "consecutive_failures": 0,
            "last_error": None,
            "provider_failures": {},
            "last_permission_refresh": None,
        }
        self._provider_failures: defaultdict[str, int] = defaultdict(int)

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

    def _check_system_permissions(self) -> dict[str, Any]:
        """Verifica el estado de permisos del sistema."""
        permissions = {
            "has_root": os.geteuid() == 0 if hasattr(os, 'geteuid') else False,
            "accessible_paths": {},
            "permission_level": "limited",
            "warnings": [],
            "is_container": self._detect_container_environment()
        }
        
        # Rutas críticas del sistema a verificar
        critical_paths = {
            "proc_meminfo": "/proc/meminfo",
            "proc_cpuinfo": "/proc/cpuinfo", 
            "proc_stat": "/proc/stat",
            "sys_dmi": "/sys/class/dmi/id/product_name",
            "sys_hwmon": "/sys/class/hwmon",
            "sys_cpu": "/sys/devices/system/cpu",
            "sys_thermal": "/sys/class/thermal",
            "proc_diskstats": "/proc/diskstats",
            "sys_block": "/sys/block"
        }
        
        accessible_count = 0
        for key, path in critical_paths.items():
            try:
                if os.path.exists(path):
                    if os.path.isdir(path):
                        # Para directorios, verificar si podemos listar
                        os.listdir(path)
                    else:
                        # Para archivos, intentar leer
                        with open(path, 'r') as f:
                            f.read(100)  # Leer los primeros 100 bytes
                    permissions["accessible_paths"][key] = True
                    accessible_count += 1
                else:
                    permissions["accessible_paths"][key] = False
            except (PermissionError, OSError):
                permissions["accessible_paths"][key] = False
                if key in ["sys_hwmon", "sys_thermal", "sys_dmi"]:
                    permissions["warnings"].append(f"Sin acceso a {path} - datos de hardware limitados")
        
        # Determinar el nivel de permisos
        total_paths = len(critical_paths)
        access_ratio = accessible_count / total_paths
        
        if permissions["has_root"]:
            permissions["permission_level"] = "full"
        elif access_ratio >= 0.8:
            permissions["permission_level"] = "good"
        elif access_ratio >= 0.5:
            permissions["permission_level"] = "partial"
        else:
            permissions["permission_level"] = "limited"
            permissions["warnings"].append("Permisos insuficientes - considere ejecutar con privilegios elevados")
        
        permissions["access_percentage"] = int(access_ratio * 100)
        
        # Ajustes para entornos contenedorizados
        if permissions["is_container"]:
            if access_ratio >= 0.6:  # Criterio más relajado para contenedores
                permissions["permission_level"] = "container_good"
                permissions["warnings"].append("Ejecutándose en contenedor - algunas métricas pueden estar limitadas")
            else:
                permissions["permission_level"] = "container_limited"
                permissions["warnings"].append("Contenedor con acceso restringido al host")
        
        return permissions

    def _detect_container_environment(self) -> bool:
        """Detecta si estamos ejecutando en un entorno contenedorizado."""
        container_indicators = [
            os.path.exists("/.dockerenv"),
            os.path.exists("/run/.containerenv"),
            "container" in os.environ,
            "DOCKER_CONTAINER" in os.environ,
            "KUBERNETES_SERVICE_HOST" in os.environ,
        ]
        
        # Verificar cgroups para contenedores
        try:
            with open("/proc/1/cgroup", "r") as f:
                cgroup_content = f.read()
                if any(indicator in cgroup_content for indicator in ["docker", "containerd", "lxc"]):
                    container_indicators.append(True)
        except (OSError, IOError):
            pass
        
        return any(container_indicators)

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="DataCollector", daemon=True)
        self._thread.start()
        self._schedule_permission_refresh()

    def stop(self, timeout: float | None = None) -> None:
        self._stop.set()
        thread = self._thread
        if thread and thread.is_alive():
            thread.join(timeout=timeout)
        self._thread = None

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            data = _snapshot_to_dict(self.current_data)
            data["permissions"] = self.permission_status
            data["diagnostics"] = {
                **self._diagnostics,
                "provider_failures": dict(self._provider_failures),
            }
            return data

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
            except Exception as exc:  # pragma: no cover - defensive guard for runtime collectors
                logger.exception("Error inesperado durante la recolección de métricas", exc_info=exc)
                self._update_diagnostics(success=False, duration=time.perf_counter() - start_time, error=exc)
            else:
                self._update_diagnostics(success=True, duration=time.perf_counter() - start_time)
            finally:
                if (time.time() - self._last_permission_refresh) > self._permission_refresh_interval:
                    self._schedule_permission_refresh()
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
        except Exception as exc:
            logger.exception("Proveedor '%s' falló durante la recolección", key, exc_info=exc)
            with self._lock:
                self._provider_failures[key] += 1
                self._diagnostics["last_error"] = {
                    "provider": key,
                    "message": str(exc),
                    "type": exc.__class__.__name__,
                    "timestamp": time.time(),
                }
                self._diagnostics["provider_failures"] = dict(self._provider_failures)
            return None
        if expected_type is list and isinstance(result, list):
            return result
        if isinstance(result, expected_type):
            return result
        return None

    def _update_diagnostics(self, *, success: bool, duration: float, error: Exception | None = None) -> None:
        now = time.time()
        with self._lock:
            self._diagnostics["last_run_started"] = now - duration
            self._diagnostics["last_run_duration"] = duration
            if success:
                self._diagnostics["last_success_at"] = now
                self._diagnostics["consecutive_failures"] = 0
                if error is None:
                    self._diagnostics.setdefault("last_error", None)
            else:
                self._diagnostics["consecutive_failures"] = self._diagnostics.get("consecutive_failures", 0) + 1
                self._diagnostics["last_error"] = {
                    "message": str(error) if error else "unknown",
                    "type": error.__class__.__name__ if error else "UnknownException",
                    "timestamp": now,
                }
            self._diagnostics["last_permission_refresh"] = self._last_permission_refresh or None

    def _schedule_permission_refresh(self) -> None:
        if self._permissions_thread and self._permissions_thread.is_alive():
            return

        def _refresh() -> None:
            try:
                status = self._check_system_permissions()
            except Exception as exc:  # pragma: no cover - defensive guard
                logger.exception("Error evaluando permisos del sistema", exc_info=exc)
                status = {
                    "permission_level": "limited",
                    "warnings": [f"Error al evaluar permisos: {exc}"],
                    "has_root": False,
                    "accessible_paths": {},
                    "access_percentage": 0,
                    "is_container": False,
                }
            with self._lock:
                self.permission_status = status
                self._last_permission_refresh = time.time()
                self._diagnostics["last_permission_refresh"] = self._last_permission_refresh

        thread = threading.Thread(target=_refresh, name="PermissionProbe", daemon=True)
        self._permissions_thread = thread
        thread.start()


collector = DataCollector()
"""Module-level collector instance used by the web server."""
