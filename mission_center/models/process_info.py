"""Process data structures."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class ProcessInfo:
    pid: int
    name: str
    status: str
    username: str | None
    create_time: float | None
    cpu_percent: float
    memory_bytes: int
    command_line: tuple[str, ...]
    nice: int | None
    io_read_bytes: int | None
    io_write_bytes: int | None
    gpu_percent: float | None = None


@dataclass(slots=True)
class ProcessSnapshot:
    timestamp: float
    processes: list[ProcessInfo] = field(default_factory=list)
    total_cpu_percent: float = 0.0
    total_memory_bytes: int = 0
