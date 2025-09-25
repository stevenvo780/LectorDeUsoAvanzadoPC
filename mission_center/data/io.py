"""System-wide IO throughput collection."""

from __future__ import annotations

import time
from typing import Any, Tuple

import psutil

from mission_center.models.resource_snapshot import IOSnapshot

_PREVIOUS_COUNTERS: Tuple[float, Any] | None = None


def collect_io_snapshot() -> IOSnapshot:
    timestamp = time.time()
    counters = psutil.disk_io_counters()
    global _PREVIOUS_COUNTERS
    if _PREVIOUS_COUNTERS is None:
        _PREVIOUS_COUNTERS = (timestamp, counters)
        return IOSnapshot(
            timestamp=timestamp,
            read_bytes_per_sec=0.0,
            write_bytes_per_sec=0.0,
            read_count_delta=0,
            write_count_delta=0,
        )

    prev_time, prev = _PREVIOUS_COUNTERS
    delta_t = max(timestamp - prev_time, 1e-6)
    read_rate = (counters.read_bytes - prev.read_bytes) / delta_t
    write_rate = (counters.write_bytes - prev.write_bytes) / delta_t
    snapshot = IOSnapshot(
        timestamp=timestamp,
        read_bytes_per_sec=read_rate,
        write_bytes_per_sec=write_rate,
        read_count_delta=counters.read_count - prev.read_count,
        write_count_delta=counters.write_count - prev.write_count,
    )
    _PREVIOUS_COUNTERS = (timestamp, counters)
    return snapshot
