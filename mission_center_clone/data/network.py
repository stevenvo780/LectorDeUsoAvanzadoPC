"""Network throughput collection."""

from __future__ import annotations

import time
from typing import Any, Dict, Tuple

import psutil

from mission_center_clone.models.resource_snapshot import NetworkInterfaceSnapshot, NetworkSnapshot

_PREV_NET_COUNTERS: Dict[str, Tuple[float, Any]] = {}


def _compute_rates(name: str, counters: Any, timestamp: float) -> tuple[float, float]:
    previous = _PREV_NET_COUNTERS.get(name)
    _PREV_NET_COUNTERS[name] = (timestamp, counters)
    if not previous:
        return 0.0, 0.0
    prev_time, prev = previous
    delta_t = timestamp - prev_time
    if delta_t <= 0:
        return 0.0, 0.0
    sent_rate = (counters.bytes_sent - prev.bytes_sent) / delta_t
    recv_rate = (counters.bytes_recv - prev.bytes_recv) / delta_t
    return sent_rate, recv_rate


def collect_network_snapshot() -> NetworkSnapshot:
    timestamp = time.time()
    stats = psutil.net_if_stats()
    addrs = psutil.net_if_addrs()
    counters = psutil.net_io_counters(pernic=True)

    interfaces: list[NetworkInterfaceSnapshot] = []
    for name, iface_counters in counters.items():
        sent_rate, recv_rate = _compute_rates(name, iface_counters, timestamp)
        iface_stats = stats.get(name)
        is_up = bool(getattr(iface_stats, "isup", False))
        address = None
        for addr in addrs.get(name, []):
            family_name = getattr(addr.family, "name", str(addr.family))
            if "AF_INET" in family_name:
                address = addr.address
                break
        interfaces.append(
            NetworkInterfaceSnapshot(
                name=name,
                is_up=is_up,
                sent_bytes_per_sec=sent_rate,
                recv_bytes_per_sec=recv_rate,
                address=address,
            )
        )

    return NetworkSnapshot(timestamp=timestamp, interfaces=interfaces)
