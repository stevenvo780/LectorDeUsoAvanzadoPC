"""Data provider package."""

from .cpu import collect_cpu_snapshot
from .disk import collect_disk_snapshot
from .gpu import collect_gpu_snapshot
from .io import collect_io_snapshot
from .memory import collect_memory_snapshot
from .network import collect_network_snapshot
from .pcie import collect_pcie_snapshot
from .processes import collect_process_snapshot
from .sensors import (
    collect_battery_snapshot,
    collect_fan_sensors,
    collect_power_sources_snapshot,
    collect_temperature_sensors,
)
from .system import collect_system_info

__all__ = [
    "collect_cpu_snapshot",
    "collect_disk_snapshot",
    "collect_gpu_snapshot",
    "collect_io_snapshot",
    "collect_memory_snapshot",
    "collect_network_snapshot",
    "collect_pcie_snapshot",
    "collect_process_snapshot",
    "collect_battery_snapshot",
    "collect_fan_sensors",
    "collect_power_sources_snapshot",
    "collect_temperature_sensors",
    "collect_system_info",
]
