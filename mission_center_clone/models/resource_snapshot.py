"""Dataclasses representing resource usage snapshots."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class CPUCoreMetric:
    core_id: int
    usage_percent: float
    frequency_mhz: float | None = None


@dataclass(slots=True)
class CPUSnapshot:
    timestamp: float
    usage_percent: float
    per_core: list[CPUCoreMetric]
    frequency_current_mhz: float | None
    frequency_max_mhz: float | None
    load_average: tuple[float, float, float] | None
    logical_cores: int
    physical_cores: int | None
    context_switches: int | None
    interrupts: int | None


@dataclass(slots=True)
class MemorySnapshot:
    timestamp: float
    total_bytes: int
    used_bytes: int
    available_bytes: int
    percent: float
    swap_total_bytes: int
    swap_used_bytes: int
    swap_percent: float


@dataclass(slots=True)
class GPUSnapshot:
    timestamp: float
    name: str
    vendor: str
    memory_total_bytes: int | None
    memory_used_bytes: int | None
    utilization_percent: float | None
    temperature_celsius: float | None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class DiskDeviceSnapshot:
    name: str
    mountpoint: str | None
    total_bytes: int | None
    used_bytes: int | None
    free_bytes: int | None
    read_bytes_per_sec: float | None
    write_bytes_per_sec: float | None


@dataclass(slots=True)
class DiskSnapshot:
    timestamp: float
    devices: list[DiskDeviceSnapshot]


@dataclass(slots=True)
class IOSnapshot:
    timestamp: float
    read_bytes_per_sec: float
    write_bytes_per_sec: float
    read_count_delta: int
    write_count_delta: int


@dataclass(slots=True)
class NetworkInterfaceSnapshot:
    name: str
    is_up: bool
    sent_bytes_per_sec: float
    recv_bytes_per_sec: float
    address: str | None


@dataclass(slots=True)
class NetworkSnapshot:
    timestamp: float
    interfaces: list[NetworkInterfaceSnapshot]


@dataclass(slots=True)
class PCIELinkSnapshot:
    address: str
    vendor: str | None
    device: str | None
    link_speed_gtps: float | None
    link_width: int | None
    max_link_speed_gtps: float | None
    max_link_width: int | None


@dataclass(slots=True)
class PCIESnapshot:
    timestamp: float
    devices: list[PCIELinkSnapshot]
