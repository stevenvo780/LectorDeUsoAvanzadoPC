"""Advanced sensors views (temperatures, fans, power)."""

from __future__ import annotations

from statistics import mean
from typing import Iterable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QLabel,
    QHeaderView,
    QProgressBar,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from mission_center_clone.core import HISTORY
from mission_center_clone.models import (
    BatterySnapshot,
    FanSensorReading,
    FanSensorsSnapshot,
    PowerSourceReading,
    PowerSourcesSnapshot,
    TemperatureSensorReading,
    TemperatureSensorsSnapshot,
)
from mission_center_clone.ui.widgets import LineHistoryChart

_C_TEMP_COLUMNS = ["Fuente", "Etiqueta", "Actual", "Alta", "Crítica"]
_C_FAN_COLUMNS = ["Fuente", "Etiqueta", "RPM"]
_C_POWER_COLUMNS = ["Fuente", "Estado", "Online", "Voltaje", "Corriente", "Potencia", "Capacidad", "Temp"]


def _format_temp(value: float | None) -> str:
    if value is None:
        return "--"
    return f"{value:.1f} °C"


def _format_rpm(value: float | None) -> str:
    if value is None:
        return "--"
    return f"{value:.0f} rpm"


def _format_bool(value: bool | None) -> str:
    if value is None:
        return "--"
    return "Sí" if value else "No"


def _format_float(value: float | None, unit: str) -> str:
    if value is None:
        return "--"
    return f"{value:.2f} {unit}"


def _flatten_temperatures(snapshot: TemperatureSensorsSnapshot) -> list[TemperatureSensorReading]:
    readings: list[TemperatureSensorReading] = []
    for group in snapshot.groups:
        readings.extend(group.readings)
    return readings


class TemperatureSensorsView(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self._chart = LineHistoryChart(
            ["Temperatura máx", "Temperatura promedio"],
            max_samples=HISTORY.medium_window,
            y_range=(0.0, 120.0),
        )

        self._table = QTableWidget(0, len(_C_TEMP_COLUMNS))
        self._table.setHorizontalHeaderLabels(_C_TEMP_COLUMNS)
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        for col in range(2, len(_C_TEMP_COLUMNS)):
            header.setSectionResizeMode(col, QHeaderView.ResizeToContents)
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)

        layout.addWidget(self._chart)
        layout.addWidget(self._table, 1)

    def update_snapshot(self, snapshot: TemperatureSensorsSnapshot) -> None:
        readings = _flatten_temperatures(snapshot)
        self._table.setRowCount(len(readings))
        for row, reading in enumerate(readings):
            values = [
                reading.source,
                reading.label or "--",
                _format_temp(reading.current_celsius),
                _format_temp(reading.high_celsius),
                _format_temp(reading.critical_celsius),
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col >= 2:
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self._table.setItem(row, col, item)

        current_values = [r.current_celsius for r in readings if r.current_celsius is not None]
        if current_values:
            max_temp = max(current_values)
            avg_temp = mean(current_values)
            self._chart.append_values({
                "Temperatura máx": max_temp,
                "Temperatura promedio": avg_temp,
            })


class FanSensorsView(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        self._chart = LineHistoryChart(
            ["RPM máx", "RPM promedio"],
            max_samples=HISTORY.medium_window,
            y_range=(0.0, 6000.0),
        )

        self._table = QTableWidget(0, len(_C_FAN_COLUMNS))
        self._table.setHorizontalHeaderLabels(_C_FAN_COLUMNS)
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)

        layout.addWidget(self._chart)
        layout.addWidget(self._table, 1)

    def update_snapshot(self, snapshot: FanSensorsSnapshot) -> None:
        readings = snapshot.readings
        self._table.setRowCount(len(readings))
        for row, reading in enumerate(readings):
            values = [
                reading.source,
                reading.label or "--",
                _format_rpm(reading.speed_rpm),
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col == 2:
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self._table.setItem(row, col, item)

        speeds = [r.speed_rpm for r in readings if r.speed_rpm is not None]
        if speeds:
            max_rpm = max(speeds)
            avg_rpm = mean(speeds)
            self._chart.append_values({
                "RPM máx": max_rpm,
                "RPM promedio": avg_rpm,
            })


class PowerSensorsView(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        self._battery_box = QGroupBox("Batería")
        battery_layout = QGridLayout(self._battery_box)
        self._battery_progress = QProgressBar()
        self._battery_status = QLabel("Sin batería detectada")
        self._battery_remaining = QLabel("Tiempo restante: --")
        self._battery_temperature = QLabel("Temperatura: --")
        battery_layout.addWidget(QLabel("Nivel"), 0, 0)
        battery_layout.addWidget(self._battery_progress, 0, 1)
        battery_layout.addWidget(self._battery_status, 1, 0, 1, 2)
        battery_layout.addWidget(self._battery_remaining, 2, 0, 1, 2)
        battery_layout.addWidget(self._battery_temperature, 3, 0, 1, 2)

        self._table = QTableWidget(0, len(_C_POWER_COLUMNS))
        self._table.setHorizontalHeaderLabels(_C_POWER_COLUMNS)
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        for col in range(2, len(_C_POWER_COLUMNS)):
            header.setSectionResizeMode(col, QHeaderView.ResizeToContents)
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)

        layout.addWidget(self._battery_box)
        layout.addWidget(self._table, 1)

    def update_battery(self, snapshot: BatterySnapshot) -> None:
        if snapshot.percent is None:
            self._battery_progress.setValue(0)
            self._battery_progress.setFormat("--")
        else:
            percent_value = max(0, min(int(snapshot.percent), 100))
            self._battery_progress.setValue(percent_value)
            self._battery_progress.setFormat(f"{snapshot.percent:.0f}%")
        status_parts: list[str] = []
        if snapshot.power_plugged is not None:
            status_parts.append("Enchufada" if snapshot.power_plugged else "Descargando")
        if snapshot.power_supply:
            status_parts.append(f"Fuente: {snapshot.power_supply}")
        if snapshot.cycle_count is not None:
            status_parts.append(f"Ciclos: {snapshot.cycle_count}")
        self._battery_status.setText(" | ".join(status_parts) if status_parts else "Sin batería detectada")

        if snapshot.secs_left is None:
            self._battery_remaining.setText("Tiempo restante: --")
        else:
            hours = int(snapshot.secs_left // 3600)
            minutes = int((snapshot.secs_left % 3600) // 60)
            self._battery_remaining.setText(f"Tiempo restante: {hours:02d}h{minutes:02d}m")

        if snapshot.temperature_celsius is None:
            self._battery_temperature.setText("Temperatura: --")
        else:
            self._battery_temperature.setText(f"Temperatura: {snapshot.temperature_celsius:.1f} °C")

    def update_power_sources(self, snapshot: PowerSourcesSnapshot) -> None:
        readings = snapshot.sources
        self._table.setRowCount(len(readings))
        for row, reading in enumerate(readings):
            values = [
                reading.name,
                reading.status or "--",
                _format_bool(reading.is_online),
                _format_float(reading.voltage_volts, "V"),
                _format_float(reading.current_amperes, "A"),
                _format_float(reading.power_watts, "W"),
                _format_float(reading.capacity_percent, "%"),
                _format_temp(reading.temperature_celsius),
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col >= 2:
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self._table.setItem(row, col, item)


class SensorsView(QWidget):
    """Tabbed container that groups all sensor-related panels."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._tabs = QTabWidget()
        self._temperature_view = TemperatureSensorsView()
        self._fan_view = FanSensorsView()
        self._power_view = PowerSensorsView()

        self._tabs.addTab(self._temperature_view, "Temperaturas")
        self._tabs.addTab(self._fan_view, "Ventiladores")
        self._tabs.addTab(self._power_view, "Energía")

        layout.addWidget(self._tabs)

    def update_temperature(self, snapshot: TemperatureSensorsSnapshot) -> None:
        self._temperature_view.update_snapshot(snapshot)

    def update_fans(self, snapshot: FanSensorsSnapshot) -> None:
        self._fan_view.update_snapshot(snapshot)

    def update_battery(self, snapshot: BatterySnapshot) -> None:
        self._power_view.update_battery(snapshot)

    def update_power_sources(self, snapshot: PowerSourcesSnapshot) -> None:
        self._power_view.update_power_sources(snapshot)
