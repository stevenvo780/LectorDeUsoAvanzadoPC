"""CPU data collection utilities."""

from __future__ import annotations

import os
import time
from typing import Iterable

import psutil

from mission_center_clone.models.resource_snapshot import CPUCoreMetric, CPUSnapshot


def _safe_load_average() -> tuple[float, float, float] | None:
    try:
        return os.getloadavg()
    except (OSError, AttributeError):  # pragma: no cover - platform specific
        return None


def _core_frequencies(freqs: Iterable[object]) -> list[float | None]:
    values: list[float | None] = []
    for freq in freqs:
        try:
            values.append(float(getattr(freq, "current")))
        except (AttributeError, TypeError):
            values.append(None)
    return values


def collect_cpu_snapshot() -> CPUSnapshot:
    """Return a CPU usage snapshot."""

    timestamp = time.time()
    usage_percent = psutil.cpu_percent(interval=None)
    percpu = psutil.cpu_percent(interval=None, percpu=True)
    freq = psutil.cpu_freq()
    freq_per_core = psutil.cpu_freq(percpu=True)
    core_freqs = _core_frequencies(freq_per_core) if freq_per_core else []
    per_core_metrics = [
        CPUCoreMetric(
            core_id=i,
            usage_percent=percent,
            frequency_mhz=core_freqs[i] if i < len(core_freqs) else None,
        )
        for i, percent in enumerate(percpu)
    ]
    cpu_stats = None
    try:
        cpu_stats = psutil.cpu_stats()
    except Exception:  # pragma: no cover - optional
        pass

    return CPUSnapshot(
        timestamp=timestamp,
        usage_percent=usage_percent,
        per_core=per_core_metrics,
        frequency_current_mhz=float(freq.current) if freq else None,
        frequency_max_mhz=float(freq.max) if freq else None,
        load_average=_safe_load_average(),
        logical_cores=psutil.cpu_count(logical=True) or len(percpu),
        physical_cores=psutil.cpu_count(logical=False),
        context_switches=getattr(cpu_stats, "ctx_switches", None) if cpu_stats else None,
        interrupts=getattr(cpu_stats, "interrupts", None) if cpu_stats else None,
    )
