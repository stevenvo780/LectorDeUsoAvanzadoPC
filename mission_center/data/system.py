"""System summary collection utilities."""

from __future__ import annotations

import platform
import socket
import time
from pathlib import Path
from typing import Optional

import psutil

from mission_center.models import SystemInfoSnapshot

from .gpu import collect_gpu_snapshot

_DMI_PATH = Path("/sys/class/dmi/id")


def _read_dmi(field: str) -> str | None:
    path = _DMI_PATH / field
    if not path.exists():
        return None
    try:
        value = path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return None
    return value or None


def _detect_virtualization() -> str | None:
    candidates = [
        (_read_dmi("product_name") or "") + " " + (_read_dmi("sys_vendor") or ""),
        (_read_dmi("product_version") or ""),
    ]
    patterns = {
        "kvm": "KVM",
        "qemu": "QEMU",
        "vmware": "VMware",
        "virtualbox": "VirtualBox",
        "hyper-v": "Hyper-V",
        "xen": "Xen",
        "parallels": "Parallels",
    }
    for text in candidates:
        lowered = text.lower()
        for needle, label in patterns.items():
            if needle in lowered:
                return label
    return None


_CHASSIS_TYPES = {
    "1": "Other",
    "2": "Unknown",
    "3": "Desktop",
    "4": "Low Profile Desktop",
    "5": "Pizza Box",
    "6": "Mini Tower",
    "7": "Tower",
    "8": "Portable",
    "9": "Laptop",
    "10": "Notebook",
    "11": "Hand Held",
    "12": "Docking Station",
    "13": "All in One",
    "14": "Sub Notebook",
    "15": "Space-saving",
    "16": "Lunch Box",
    "17": "Main Server Chassis",
    "18": "Expansion Chassis",
    "19": "SubChassis",
    "20": "Bus Expansion Chassis",
    "21": "Peripheral Chassis",
    "22": "Storage Chassis",
    "23": "Rack Mount Chassis",
    "24": "Sealed-case PC",
    "25": "Multi-system",
    "26": "CompactPCI",
    "27": "AdvancedTCA",
    "28": "Blade",
    "29": "Blade Enclosure",
    "30": "Tablet",
    "31": "Convertible",
    "32": "Detachable",
    "33": "IoT Gateway",
    "34": "Embedded PC",
    "35": "Mini PC",
    "36": "Stick PC",
}


def collect_system_info() -> SystemInfoSnapshot:
    timestamp = time.time()
    uname = platform.uname()
    hostname = getattr(uname, "node", None) or socket.gethostname()
    os_name = platform.system() or None
    os_version = platform.version() or None
    kernel_version = getattr(uname, "release", None)
    architecture = getattr(uname, "machine", None)
    cpu_model = getattr(uname, "processor", None) or platform.processor() or None

    logical_cores = psutil.cpu_count(logical=True)
    physical_cores = psutil.cpu_count(logical=False)

    try:
        total_memory_bytes = int(psutil.virtual_memory().total)
    except Exception:  # pragma: no cover - should not happen
        total_memory_bytes = None

    boot_time: Optional[float]
    try:
        boot_time = float(psutil.boot_time())
    except Exception:  # pragma: no cover - psutil fallback
        boot_time = None

    uptime_seconds = None
    if boot_time:
        uptime_seconds = max(0.0, timestamp - boot_time)

    bios_vendor = _read_dmi("bios_vendor")
    bios_version = _read_dmi("bios_version")
    bios_date = _read_dmi("bios_date")
    motherboard = _read_dmi("board_name") or _read_dmi("baseboard_product")
    system_manufacturer = _read_dmi("sys_vendor")
    system_model = _read_dmi("product_name")
    chassis_code = _read_dmi("chassis_type") or _read_dmi("chassis_type_enclosure")
    chassis_type = _CHASSIS_TYPES.get(chassis_code, chassis_code)

    virtualization = _detect_virtualization()

    gpu_devices: list[str] = []
    try:
        gpu_snapshots = collect_gpu_snapshot()
    except Exception:  # pragma: no cover - optional NVML
        gpu_snapshots = []
    for gpu in gpu_snapshots:
        device_name = gpu.name
        if gpu.vendor:
            device_name = f"{gpu.vendor} {device_name}" if device_name else gpu.vendor
        if device_name:
            gpu_devices.append(device_name)

    return SystemInfoSnapshot(
        timestamp=timestamp,
        hostname=hostname,
        os_name=os_name,
        os_version=os_version,
        kernel_version=kernel_version,
        architecture=architecture,
        cpu_model=cpu_model,
        logical_cores=logical_cores,
        physical_cores=physical_cores,
        total_memory_bytes=total_memory_bytes,
        uptime_seconds=uptime_seconds,
        boot_time=boot_time,
        bios_vendor=bios_vendor,
        bios_version=bios_version,
        bios_date=bios_date,
        motherboard=motherboard,
        system_manufacturer=system_manufacturer,
        system_model=system_model,
        chassis_type=chassis_type,
        virtualization=virtualization,
        gpu_devices=gpu_devices,
    )
