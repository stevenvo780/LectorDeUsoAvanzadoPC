"""PCIe topology and link metrics collection."""

from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Iterable

from mission_center_clone.models.resource_snapshot import PCIELinkSnapshot, PCIESnapshot

try:
    import pyudev  # type: ignore[import]
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    pyudev = None  # type: ignore[assignment]

_SYS_PCI = Path("/sys/bus/pci/devices")
_SPEED_RE = re.compile(r"([0-9.]+)")
_WIDTH_RE = re.compile(r"(\d+)")


def _parse_speed(value: str | None) -> float | None:
    if not value:
        return None
    match = _SPEED_RE.search(value)
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


def _parse_width(value: str | None) -> int | None:
    if not value:
        return None
    match = _WIDTH_RE.search(value)
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def _collect_pyudev() -> Iterable[PCIELinkSnapshot]:
    assert pyudev is not None
    ctx = pyudev.Context()
    for device in ctx.list_devices(subsystem="pci"):
        attrs = device.attributes
        current_speed = attrs.get("current_link_speed")
        current_width = attrs.get("current_link_width")
        max_speed = attrs.get("max_link_speed")
        max_width = attrs.get("max_link_width")
        vendor = attrs.get("vendor")
        dev = attrs.get("device")
        yield PCIELinkSnapshot(
            address=device.sys_name,
            vendor=str(vendor) if vendor else None,
            device=str(dev) if dev else None,
            link_speed_gtps=_parse_speed(
                current_speed.decode() if isinstance(current_speed, bytes) else str(current_speed)
            ),
            link_width=_parse_width(
                current_width.decode() if isinstance(current_width, bytes) else str(current_width)
            ),
            max_link_speed_gtps=_parse_speed(
                max_speed.decode() if isinstance(max_speed, bytes) else str(max_speed)
            ),
            max_link_width=_parse_width(
                max_width.decode() if isinstance(max_width, bytes) else str(max_width)
            ),
        )


def _collect_sysfs() -> Iterable[PCIELinkSnapshot]:
    if not _SYS_PCI.exists():
        return []
    for device_path in _SYS_PCI.iterdir():
        def safe_read(p: Path) -> str | None:
            try:
                return p.read_text().strip()
            except Exception:
                return None

        current_speed = safe_read(device_path / "current_link_speed") if (device_path / "current_link_speed").exists() else None
        current_width = safe_read(device_path / "current_link_width") if (device_path / "current_link_width").exists() else None
        max_speed = safe_read(device_path / "max_link_speed") if (device_path / "max_link_speed").exists() else None
        max_width = safe_read(device_path / "max_link_width") if (device_path / "max_link_width").exists() else None
        vendor = safe_read(device_path / "vendor") if (device_path / "vendor").exists() else None
        device = safe_read(device_path / "device") if (device_path / "device").exists() else None
        yield PCIELinkSnapshot(
            address=device_path.name,
            vendor=vendor,
            device=device,
            link_speed_gtps=_parse_speed(current_speed),
            link_width=_parse_width(current_width),
            max_link_speed_gtps=_parse_speed(max_speed),
            max_link_width=_parse_width(max_width),
        )


def collect_pcie_snapshot() -> PCIESnapshot:
    timestamp = time.time()
    devices: list[PCIELinkSnapshot] = []
    if pyudev is not None:
        devices.extend(_collect_pyudev())
    if not devices:
        devices.extend(_collect_sysfs())
    return PCIESnapshot(timestamp=timestamp, devices=devices)
