"""GPU data provider with optional NVML support."""

from __future__ import annotations

import time
from typing import Iterator

from mission_center_clone.models.resource_snapshot import GPUSnapshot

try:
    import pynvml  # type: ignore[import]
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    pynvml = None  # type: ignore[assignment]


def _iter_nvml_handles() -> Iterator[int]:
    assert pynvml is not None
    count = pynvml.nvmlDeviceGetCount()
    for index in range(count):
        yield pynvml.nvmlDeviceGetHandleByIndex(index)


def collect_gpu_snapshot() -> list[GPUSnapshot]:
    """Collect GPU information; returns an empty list if no backend is available."""

    timestamp = time.time()
    snapshots: list[GPUSnapshot] = []
    if pynvml is None:
        return snapshots

    pynvml.nvmlInit()
    try:
        for handle in _iter_nvml_handles():
            name = pynvml.nvmlDeviceGetName(handle).decode("utf-8")
            vendor = "NVIDIA"
            memory = pynvml.nvmlDeviceGetMemoryInfo(handle)
            util = pynvml.nvmlDeviceGetUtilizationRates(handle)
            temperature = pynvml.nvmlDeviceGetTemperature(
                handle, pynvml.NVML_TEMPERATURE_GPU
            )
            extra = {
                "graphics_clock_mhz": pynvml.nvmlDeviceGetClockInfo(
                    handle, pynvml.NVML_CLOCK_GRAPHICS
                ),
                "sm_clock_mhz": pynvml.nvmlDeviceGetClockInfo(
                    handle, pynvml.NVML_CLOCK_SM
                ),
            }
            snapshots.append(
                GPUSnapshot(
                    timestamp=timestamp,
                    name=name,
                    vendor=vendor,
                    memory_total_bytes=int(memory.total),
                    memory_used_bytes=int(memory.used),
                    utilization_percent=float(util.gpu),
                    temperature_celsius=float(temperature),
                    extra=extra,
                )
            )
    finally:
        pynvml.nvmlShutdown()

    return snapshots
