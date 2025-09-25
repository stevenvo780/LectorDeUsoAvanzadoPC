"""GPU data provider with multiple backend support."""

from __future__ import annotations

import subprocess
import time
from typing import Iterator

from mission_center.models.resource_snapshot import GPUSnapshot

try:
    import pynvml  # type: ignore[import]
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    pynvml = None  # type: ignore[assignment]


def _iter_nvml_handles() -> Iterator[int]:
    assert pynvml is not None
    count = pynvml.nvmlDeviceGetCount()
    for index in range(count):
        yield pynvml.nvmlDeviceGetHandleByIndex(index)


def _collect_nvidia_smi_data() -> list[GPUSnapshot]:
    """Collect NVIDIA GPU data using nvidia-smi command."""
    timestamp = time.time()
    snapshots: list[GPUSnapshot] = []
    
    try:
        # Query nvidia-smi for GPU data
        cmd = [
            "nvidia-smi",
            "--query-gpu=name,utilization.gpu,memory.total,memory.used,temperature.gpu,clocks.current.graphics,clocks.current.memory",
            "--format=csv,noheader,nounits"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        
        if result.returncode != 0:
            return snapshots
            
        for line in result.stdout.strip().split('\n'):
            if not line.strip():
                continue
                
            parts = [p.strip() for p in line.split(',')]
            if len(parts) >= 5:
                name = parts[0]
                utilization = float(parts[1]) if parts[1] != "[Not Supported]" else 0.0
                memory_total = int(parts[2]) * 1024 * 1024  # Convert MiB to bytes
                memory_used = int(parts[3]) * 1024 * 1024   # Convert MiB to bytes
                temperature = float(parts[4]) if parts[4] != "[Not Supported]" else 0.0
                graphics_clock = float(parts[5]) if len(parts) > 5 and parts[5] != "[Not Supported]" else 0.0
                memory_clock = float(parts[6]) if len(parts) > 6 and parts[6] != "[Not Supported]" else 0.0
                
                extra = {
                    "graphics_clock_mhz": graphics_clock,
                    "memory_clock_mhz": memory_clock,
                }
                
                snapshots.append(
                    GPUSnapshot(
                        timestamp=timestamp,
                        name=name,
                        vendor="NVIDIA",
                        memory_total_bytes=memory_total,
                        memory_used_bytes=memory_used,
                        utilization_percent=utilization,
                        temperature_celsius=temperature,
                        extra=extra,
                    )
                )
    except (subprocess.SubprocessError, ValueError, IndexError):
        pass  # Fall back to empty list
        
    return snapshots


def _collect_pynvml_data() -> list[GPUSnapshot]:
    """Collect GPU data using pynvml library."""
    timestamp = time.time()
    snapshots: list[GPUSnapshot] = []
    
    if pynvml is None:
        return snapshots

    try:
        pynvml.nvmlInit()
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
    except Exception:
        pass  # Fall back to empty list
    finally:
        try:
            pynvml.nvmlShutdown()
        except Exception:
            pass

    return snapshots


def collect_gpu_snapshot() -> list[GPUSnapshot]:
    """Collect GPU information using available backends."""
    
    # Try nvidia-smi first (more reliable and doesn't require Python bindings)
    snapshots = _collect_nvidia_smi_data()
    if snapshots:
        return snapshots
    
    # Fallback to pynvml
    snapshots = _collect_pynvml_data()
    if snapshots:
        return snapshots
        
    # No GPU data available
    return []
