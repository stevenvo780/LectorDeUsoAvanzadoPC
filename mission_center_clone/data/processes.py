"""Process list collection mimicking Mission Center grouping."""

from __future__ import annotations

import time
from typing import Iterable

import psutil

from mission_center_clone.models.process_info import ProcessInfo, ProcessSnapshot

_PROCESS_ATTRS = [
    "pid",
    "name",
    "status",
    "username",
    "create_time",
    "cpu_percent",
    "memory_info",
    "cmdline",
    "nice",
    "io_counters",
]


def _safe_cmdline(cmdline: Iterable[str] | None) -> tuple[str, ...]:
    if not cmdline:
        return ()
    return tuple(arg for arg in cmdline if arg)


def collect_process_snapshot() -> ProcessSnapshot:
    timestamp = time.time()
    processes: list[ProcessInfo] = []
    total_cpu = 0.0
    total_mem = 0
    for proc in psutil.process_iter(attrs=_PROCESS_ATTRS):
        try:
            info = proc.info
            memory_info = info.get("memory_info")
            memory_bytes = int(memory_info.rss) if memory_info else 0
            cpu_percent = float(info.get("cpu_percent") or proc.cpu_percent(interval=None))
            io_counters = info.get("io_counters")
            read_bytes = int(io_counters.read_bytes) if io_counters else None
            write_bytes = int(io_counters.write_bytes) if io_counters else None
            processes.append(
                ProcessInfo(
                    pid=int(info["pid"]),
                    name=str(info.get("name") or ""),
                    status=str(info.get("status") or "unknown"),
                    username=info.get("username"),
                    create_time=float(info.get("create_time") or 0.0),
                    cpu_percent=cpu_percent,
                    memory_bytes=memory_bytes,
                    command_line=_safe_cmdline(info.get("cmdline")),
                    nice=int(info.get("nice")) if info.get("nice") is not None else None,
                    io_read_bytes=read_bytes,
                    io_write_bytes=write_bytes,
                )
            )
            total_cpu += cpu_percent
            total_mem += memory_bytes
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    processes.sort(key=lambda p: (p.cpu_percent, p.memory_bytes), reverse=True)
    return ProcessSnapshot(
        timestamp=timestamp,
        processes=processes,
        total_cpu_percent=total_cpu,
        total_memory_bytes=total_mem,
    )
