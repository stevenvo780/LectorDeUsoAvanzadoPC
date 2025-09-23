"""Disk storage and per-device throughput collection."""

from __future__ import annotations

import time
from typing import Any, Dict, Tuple

import psutil

from mission_center_clone.models.resource_snapshot import DiskDeviceSnapshot, DiskSnapshot

_LAST_DISK_COUNTERS: Dict[str, Tuple[float, Any]] = {}


def _device_rates(name: str, counters: Any, timestamp: float) -> tuple[float | None, float | None]:
    previous = _LAST_DISK_COUNTERS.get(name)
    _LAST_DISK_COUNTERS[name] = (timestamp, counters)
    if not previous:
        return None, None
    prev_time, prev = previous
    delta_t = timestamp - prev_time
    if delta_t <= 0:
        return None, None
    read_rate = (counters.read_bytes - prev.read_bytes) / delta_t
    write_rate = (counters.write_bytes - prev.write_bytes) / delta_t
    return read_rate, write_rate


def collect_disk_snapshot() -> DiskSnapshot:
    timestamp = time.time()
    partitions = {part.device: part.mountpoint for part in psutil.disk_partitions(all=False)}
    usage_cache: Dict[str, tuple[int | None, int | None, int | None]] = {}
    devices: list[DiskDeviceSnapshot] = []
    per_disk_counters = psutil.disk_io_counters(perdisk=True)

    for device_name, counters in per_disk_counters.items():
        device_path = f"/dev/{device_name}" if not device_name.startswith("/dev/") else device_name
        mountpoint = partitions.get(device_path)
        if mountpoint and mountpoint not in usage_cache:
            try:
                usage = psutil.disk_usage(mountpoint)
                usage_cache[mountpoint] = (
                    int(usage.total),
                    int(usage.used),
                    int(usage.free),
                )
            except PermissionError:  # pragma: no cover - mountpoint permissions
                usage_cache[mountpoint] = (None, None, None)
        total, used, free = usage_cache.get(mountpoint, (None, None, None))
        read_rate, write_rate = _device_rates(device_name, counters, timestamp)
        devices.append(
            DiskDeviceSnapshot(
                name=device_name,
                mountpoint=mountpoint,
                total_bytes=total,
                used_bytes=used,
                free_bytes=free,
                read_bytes_per_sec=read_rate,
                write_bytes_per_sec=write_rate,
            )
        )

    return DiskSnapshot(timestamp=timestamp, devices=devices)
