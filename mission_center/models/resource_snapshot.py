"""Dataclasses representing resource usage snapshots."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class TemperatureSensorReading:
    source: str
    label: str | None
    current_celsius: float | None
    high_celsius: float | None
    critical_celsius: float | None


@dataclass(slots=True)
class TemperatureSensorGroup:
    name: str
    readings: list[TemperatureSensorReading] = field(default_factory=list)


@dataclass(slots=True)
class TemperatureSensorsSnapshot:
    timestamp: float
    groups: list[TemperatureSensorGroup] = field(default_factory=list)


@dataclass(slots=True)
class FanSensorReading:
    source: str
    label: str | None
    speed_rpm: float | None


@dataclass(slots=True)
class FanSensorsSnapshot:
    timestamp: float
    readings: list[FanSensorReading] = field(default_factory=list)


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


@dataclass(slots=True)
class BatterySnapshot:
    timestamp: float
    percent: float | None
    secs_left: float | None
    power_plugged: bool | None
    cycle_count: int | None = None
    power_supply: str | None = None
    energy_full_wh: float | None = None
    energy_now_wh: float | None = None
    temperature_celsius: float | None = None


@dataclass(slots=True)
class PowerSourceReading:
    name: str
    status: str | None
    is_online: bool | None
    voltage_volts: float | None
    current_amperes: float | None
    power_watts: float | None
    capacity_percent: float | None
    temperature_celsius: float | None


@dataclass(slots=True)
class PowerSourcesSnapshot:
    timestamp: float
    sources: list[PowerSourceReading] = field(default_factory=list)


@dataclass(slots=True)
class SystemInfoSnapshot:
    timestamp: float
    hostname: str | None
    os_name: str | None
    os_version: str | None
    kernel_version: str | None
    architecture: str | None
    cpu_model: str | None
    logical_cores: int | None
    physical_cores: int | None
    total_memory_bytes: int | None
    uptime_seconds: float | None
    boot_time: float | None
    bios_vendor: str | None = None
    bios_version: str | None = None
    bios_date: str | None = None
    motherboard: str | None = None
    system_manufacturer: str | None = None
    system_model: str | None = None
    chassis_type: str | None = None
    virtualization: str | None = None
    gpu_devices: list[str] = field(default_factory=list)
