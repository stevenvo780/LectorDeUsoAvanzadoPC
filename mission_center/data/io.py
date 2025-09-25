"""System-wide IO throughput collection with per-device statistics."""

from __future__ import annotations

import time
from typing import Any, Dict, Tuple

import psutil

from mission_center.models.resource_snapshot import IOSnapshot

_PREVIOUS_COUNTERS: Tuple[float, Any] | None = None
_PREVIOUS_PER_DEVICE: Tuple[float, Dict[str, Any]] | None = None


def collect_io_snapshot() -> IOSnapshot:
    timestamp = time.time()
    counters = psutil.disk_io_counters()
    per_device_counters = psutil.disk_io_counters(perdisk=True)
    
    global _PREVIOUS_COUNTERS, _PREVIOUS_PER_DEVICE
    
    # System-wide I/O
    if _PREVIOUS_COUNTERS is None:
        _PREVIOUS_COUNTERS = (timestamp, counters)
        read_rate = 0.0
        write_rate = 0.0
        read_count_delta = 0
        write_count_delta = 0
    else:
        prev_time, prev = _PREVIOUS_COUNTERS
        delta_t = max(timestamp - prev_time, 1e-6)
        read_rate = (counters.read_bytes - prev.read_bytes) / delta_t
        write_rate = (counters.write_bytes - prev.write_bytes) / delta_t
        read_count_delta = counters.read_count - prev.read_count
        write_count_delta = counters.write_count - prev.write_count
        _PREVIOUS_COUNTERS = (timestamp, counters)
    
    # Per-device I/O statistics
    per_device_stats = {}
    if _PREVIOUS_PER_DEVICE is None:
        _PREVIOUS_PER_DEVICE = (timestamp, per_device_counters)
        for device, device_counters in per_device_counters.items():
            per_device_stats[device] = {
                "read_bytes_per_sec": 0.0,
                "write_bytes_per_sec": 0.0,
                "read_count_per_sec": 0.0,
                "write_count_per_sec": 0.0,
                "read_time_ms": device_counters.read_time,
                "write_time_ms": device_counters.write_time,
                "busy_time_ms": getattr(device_counters, 'busy_time', 0),
            }
    else:
        prev_time_device, prev_device = _PREVIOUS_PER_DEVICE
        delta_t_device = max(timestamp - prev_time_device, 1e-6)
        
        for device, device_counters in per_device_counters.items():
            if device in prev_device:
                prev_device_counters = prev_device[device]
                device_read_rate = (device_counters.read_bytes - prev_device_counters.read_bytes) / delta_t_device
                device_write_rate = (device_counters.write_bytes - prev_device_counters.write_bytes) / delta_t_device
                device_read_ops = (device_counters.read_count - prev_device_counters.read_count) / delta_t_device
                device_write_ops = (device_counters.write_count - prev_device_counters.write_count) / delta_t_device
                
                per_device_stats[device] = {
                    "read_bytes_per_sec": device_read_rate,
                    "write_bytes_per_sec": device_write_rate,
                    "read_count_per_sec": device_read_ops,
                    "write_count_per_sec": device_write_ops,
                    "read_time_ms": device_counters.read_time,
                    "write_time_ms": device_counters.write_time,
                    "busy_time_ms": getattr(device_counters, 'busy_time', 0),
                    "utilization_percent": min(100.0, ((device_counters.read_time + device_counters.write_time) - 
                                                      (prev_device_counters.read_time + prev_device_counters.write_time)) / 
                                                      (delta_t_device * 1000) * 100) if delta_t_device > 0 else 0.0,
                }
            else:
                per_device_stats[device] = {
                    "read_bytes_per_sec": 0.0,
                    "write_bytes_per_sec": 0.0,
                    "read_count_per_sec": 0.0,
                    "write_count_per_sec": 0.0,
                    "read_time_ms": device_counters.read_time,
                    "write_time_ms": device_counters.write_time,
                    "busy_time_ms": getattr(device_counters, 'busy_time', 0),
                    "utilization_percent": 0.0,
                }
        
        _PREVIOUS_PER_DEVICE = (timestamp, per_device_counters)
    
    snapshot = IOSnapshot(
        timestamp=timestamp,
        read_bytes_per_sec=read_rate,
        write_bytes_per_sec=write_rate,
        read_count_delta=read_count_delta,
        write_count_delta=write_count_delta,
        per_device=per_device_stats,
    )
    
    return snapshot
