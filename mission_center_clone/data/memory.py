"""Memory data collection."""

from __future__ import annotations

import time

import psutil

from mission_center_clone.models.resource_snapshot import MemorySnapshot


def collect_memory_snapshot() -> MemorySnapshot:
    timestamp = time.time()
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()
    return MemorySnapshot(
        timestamp=timestamp,
        total_bytes=int(mem.total),
        used_bytes=int(mem.total - mem.available),
        available_bytes=int(mem.available),
        percent=float(mem.percent),
        swap_total_bytes=int(swap.total),
        swap_used_bytes=int(swap.used),
        swap_percent=float(swap.percent),
    )
