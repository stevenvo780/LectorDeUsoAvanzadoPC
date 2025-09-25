"""Hardware sensor collectors beyond basic CPU/GPU metrics."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Iterable

import psutil

from mission_center.models import (
    BatterySnapshot,
    FanSensorReading,
    FanSensorsSnapshot,
    PowerSourceReading,
    PowerSourcesSnapshot,
    TemperatureSensorGroup,
    TemperatureSensorReading,
    TemperatureSensorsSnapshot,
)

_SYS_POWER_SUPPLY = Path("/sys/class/power_supply")


def _temperature_reading(source: str, entry: object) -> TemperatureSensorReading:
    def _coerce(name: str) -> float | None:
        value = getattr(entry, name, None)
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    label = getattr(entry, "label", None)
    label_str = str(label) if label else None
    return TemperatureSensorReading(
        source=source,
        label=label_str if label_str else None,
        current_celsius=_coerce("current"),
        high_celsius=_coerce("high"),
        critical_celsius=_coerce("critical"),
    )


def collect_temperature_sensors() -> TemperatureSensorsSnapshot:
    """Collect temperature sensors exposed by psutil.

    The function gracefully handles platforms without sensor support by
    returning an empty snapshot.
    """

    timestamp = time.time()
    groups: list[TemperatureSensorGroup] = []
    try:
        sensors = psutil.sensors_temperatures(fahrenheit=False)
    except (AttributeError, NotImplementedError):  # pragma: no cover - platform specific
        sensors = {}
    for name, entries in sensors.items():
        readings = [_temperature_reading(name, entry) for entry in entries]
        if readings:
            groups.append(TemperatureSensorGroup(name=name, readings=readings))
    return TemperatureSensorsSnapshot(timestamp=timestamp, groups=groups)


def _fan_reading(source: str, entry: object) -> FanSensorReading:
    speed = getattr(entry, "current", None)
    try:
        rpm = float(speed) if speed is not None else None
    except (TypeError, ValueError):
        rpm = None
    label = getattr(entry, "label", None)
    label_str = str(label) if label else None
    return FanSensorReading(
        source=source,
        label=label_str if label_str else None,
        speed_rpm=rpm,
    )


def collect_fan_sensors() -> FanSensorsSnapshot:
    timestamp = time.time()
    readings: list[FanSensorReading] = []
    try:
        fans = psutil.sensors_fans()
    except (AttributeError, NotImplementedError):  # pragma: no cover - platform specific
        fans = {}
    for name, entries in fans.items():
        readings.extend(_fan_reading(name, entry) for entry in entries)
    return FanSensorsSnapshot(timestamp=timestamp, readings=readings)


def _read_text(path: Path) -> str | None:
    try:
        value = path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return None
    return value or None


def _read_float(path: Path, scale: float | None = None) -> float | None:
    text = _read_text(path)
    if text is None:
        return None
    try:
        value = float(text)
    except ValueError:
        return None
    if scale:
        value /= scale
    return value


def _read_int(path: Path) -> int | None:
    text = _read_text(path)
    if text is None:
        return None
    try:
        return int(float(text))
    except ValueError:
        return None


def _detect_temperature(value: float | None) -> float | None:
    if value is None:
        return None
    if value > 1000:  # heurística para milésimas
        return value / 1000.0
    if value > 200:  # heurística para décimas
        return value / 10.0
    return value


def collect_power_sources_snapshot() -> PowerSourcesSnapshot:
    timestamp = time.time()
    sources: list[PowerSourceReading] = []
    if _SYS_POWER_SUPPLY.exists():
        for entry in _SYS_POWER_SUPPLY.iterdir():
            if not entry.is_dir():
                continue
            name = entry.name
            status = _read_text(entry / "status")
            online = _read_int(entry / "online")
            voltage = _read_float(entry / "voltage_now", scale=1_000_000)
            current = _read_float(entry / "current_now", scale=1_000_000)
            power = _read_float(entry / "power_now", scale=1_000_000)
            capacity = _read_float(entry / "capacity")
            temperature = _detect_temperature(_read_float(entry / "temp"))
            if power is None and voltage is not None and current is not None:
                power = voltage * current
            sources.append(
                PowerSourceReading(
                    name=name,
                    status=status,
                    is_online=bool(online) if online is not None else None,
                    voltage_volts=voltage,
                    current_amperes=current,
                    power_watts=power,
                    capacity_percent=capacity,
                    temperature_celsius=temperature,
                )
            )
    if not sources:
        # Fallback: at least surface the battery if available
        try:
            battery = psutil.sensors_battery()
        except (AttributeError, NotImplementedError):  # pragma: no cover
            battery = None
        if battery is not None:
            sources.append(
                PowerSourceReading(
                    name="battery",
                    status="charging" if battery.power_plugged else "discharging",
                    is_online=battery.power_plugged,
                    voltage_volts=None,
                    current_amperes=None,
                    power_watts=None,
                    capacity_percent=float(battery.percent) if battery.percent is not None else None,
                    temperature_celsius=None,
                )
            )
    return PowerSourcesSnapshot(timestamp=timestamp, sources=sources)


def collect_battery_snapshot() -> BatterySnapshot:
    timestamp = time.time()
    try:
        battery = psutil.sensors_battery()
    except (AttributeError, NotImplementedError):  # pragma: no cover - optional
        battery = None
    percent: float | None = None
    secs_left: float | None = None
    plugged: bool | None = None
    if battery is not None:
        percent = float(battery.percent) if battery.percent is not None else None
        secs = battery.secsleft
        if secs in (psutil.POWER_TIME_UNKNOWN, psutil.POWER_TIME_UNLIMITED):
            secs_left = None
        elif secs is not None and secs >= 0:
            secs_left = float(secs)
        plugged = bool(battery.power_plugged)

    cycle_count: int | None = None
    energy_full: float | None = None
    energy_now: float | None = None
    temperature: float | None = None
    supply_name: str | None = None

    if _SYS_POWER_SUPPLY.exists():
        batteries: Iterable[Path] = [p for p in _SYS_POWER_SUPPLY.iterdir() if p.is_dir()]
        for entry in batteries:
            entry_type = _read_text(entry / "type")
            if entry_type and entry_type.lower() != "battery":
                continue
            supply_name = entry.name
            cycle_count = _read_int(entry / "cycle_count") or cycle_count
            energy_full = _read_float(entry / "energy_full", scale=1_000_000) or energy_full
            energy_now = _read_float(entry / "energy_now", scale=1_000_000) or energy_now
            temperature = _detect_temperature(_read_float(entry / "temp")) or temperature
            break

    return BatterySnapshot(
        timestamp=timestamp,
        percent=percent,
        secs_left=secs_left,
        power_plugged=plugged,
        cycle_count=cycle_count,
        power_supply=supply_name,
        energy_full_wh=energy_full,
        energy_now_wh=energy_now,
        temperature_celsius=temperature,
    )
