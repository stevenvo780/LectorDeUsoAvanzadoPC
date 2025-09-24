"""Main window replicating Mission Center navigation."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from PySide6.QtWidgets import (
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QStackedWidget,
    QTabWidget,
    QWidget,
)

from mission_center_clone.core import CONFIG, DataUpdateCoordinator, load_stylesheet
from mission_center_clone.data import (
    collect_battery_snapshot,
    collect_cpu_snapshot,
    collect_disk_snapshot,
    collect_fan_sensors,
    collect_gpu_snapshot,
    collect_io_snapshot,
    collect_memory_snapshot,
    collect_network_snapshot,
    collect_pcie_snapshot,
    collect_power_sources_snapshot,
    collect_process_snapshot,
    collect_system_info,
    collect_temperature_sensors,
)
from mission_center_clone.models import (
    BatterySnapshot,
    CPUSnapshot,
    DiskSnapshot,
    FanSensorsSnapshot,
    GPUSnapshot,
    IOSnapshot,
    MemorySnapshot,
    NetworkSnapshot,
    PCIESnapshot,
    PowerSourcesSnapshot,
    ProcessSnapshot,
    SystemInfoSnapshot,
    TemperatureSensorsSnapshot,
)
from mission_center_clone.ui.dashboard import DashboardView
from mission_center_clone.ui.performance.cpu_view import CPUPerformanceView
from mission_center_clone.ui.performance.disk_view import DiskPerformanceView
from mission_center_clone.ui.performance.gpu_view import GPUPerformanceView
from mission_center_clone.ui.performance.io_view import IOPerformanceView
from mission_center_clone.ui.performance.memory_view import MemoryPerformanceView
from mission_center_clone.ui.performance.network_view import NetworkPerformanceView
from mission_center_clone.ui.performance.pcie_view import PCIEPerformanceView
from mission_center_clone.ui.processes import ProcessesView
from mission_center_clone.ui.sensors import SensorsView
from mission_center_clone.ui.system_info import SystemInfoView


class MainWindow(QMainWindow):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Mission Center Clone")
        self.resize(1280, 720)
        self.setStyleSheet(load_stylesheet())

        self._central = QWidget(self)
        self.setCentralWidget(self._central)
        layout = QHBoxLayout(self._central)
        layout.setContentsMargins(0, 0, 0, 0)

        self._nav = QListWidget()
        self._nav.setFixedWidth(220)
        self._nav.addItem(QListWidgetItem("Panel general"))
        self._nav.addItem(QListWidgetItem("Procesos"))
        self._nav.addItem(QListWidgetItem("Rendimiento"))
        self._nav.addItem(QListWidgetItem("Sensores"))
        self._nav.addItem(QListWidgetItem("Sistema"))
        self._nav.setCurrentRow(0)
        layout.addWidget(self._nav)

        self._stack = QStackedWidget()
        layout.addWidget(self._stack, 1)

        self._dashboard = DashboardView()
        self._processes = ProcessesView()
        self._performance_tabs = QTabWidget()
        self._performance_tabs.setDocumentMode(True)
        self._sensors_view = SensorsView()
        self._system_view = SystemInfoView()

        self._cpu_view = CPUPerformanceView()
        self._memory_view = MemoryPerformanceView()
        self._gpu_view = GPUPerformanceView()
        self._disk_view = DiskPerformanceView()
        self._network_view = NetworkPerformanceView()
        self._io_view = IOPerformanceView()
        self._pcie_view = PCIEPerformanceView()

        self._performance_tabs.addTab(self._cpu_view, "CPU")
        self._performance_tabs.addTab(self._memory_view, "Memoria")
        self._performance_tabs.addTab(self._gpu_view, "GPU")
        self._performance_tabs.addTab(self._disk_view, "Almacenamiento")
        self._performance_tabs.addTab(self._network_view, "Red")
        self._performance_tabs.addTab(self._io_view, "IO")
        self._performance_tabs.addTab(self._pcie_view, "PCIe")

        self._stack.addWidget(self._dashboard)
        self._stack.addWidget(self._processes)
        self._stack.addWidget(self._performance_tabs)
        self._stack.addWidget(self._sensors_view)
        self._stack.addWidget(self._system_view)

        self._nav.currentRowChanged.connect(self._stack.setCurrentIndex)

        providers: Mapping[str, Callable[[], Any]] = {
            "cpu": collect_cpu_snapshot,
            "memory": collect_memory_snapshot,
            "gpu": collect_gpu_snapshot,
            "disk": collect_disk_snapshot,
            "io": collect_io_snapshot,
            "network": collect_network_snapshot,
            "pcie": collect_pcie_snapshot,
            "temperature": collect_temperature_sensors,
            "fans": collect_fan_sensors,
            "battery": collect_battery_snapshot,
            "power": collect_power_sources_snapshot,
            "system": collect_system_info,
            "processes": collect_process_snapshot,
        }
        intervals = {
            "cpu": CONFIG.fast,
            "memory": CONFIG.fast,
            "processes": CONFIG.fast,
            "gpu": CONFIG.medium,
            "disk": CONFIG.medium,
            "io": CONFIG.medium,
            "network": CONFIG.medium,
            "pcie": CONFIG.slow,
            "temperature": CONFIG.medium,
            "fans": CONFIG.medium,
            "battery": CONFIG.slow,
            "power": CONFIG.slow,
            "system": CONFIG.slow * 2,
        }
        self._coordinator = DataUpdateCoordinator(providers, intervals, self)
        self._coordinator.snapshot_updated.connect(self._on_snapshot)
        for key in providers:
            self._coordinator.request_refresh(key)

    def _on_snapshot(self, key: str, snapshot: Any) -> None:  # noqa: ANN401 type is runtime dynamic
        if isinstance(snapshot, Exception):
            self.statusBar().showMessage(f"Error al actualizar {key}: {snapshot}")
            return

        if key == "cpu" and isinstance(snapshot, CPUSnapshot):
            self._dashboard.update_cpu(snapshot)
            self._cpu_view.update_snapshot(snapshot)
        elif key == "memory" and isinstance(snapshot, MemorySnapshot):
            self._dashboard.update_memory(snapshot)
            self._memory_view.update_snapshot(snapshot)
        elif key == "gpu" and isinstance(snapshot, list):
            self._dashboard.update_gpu(snapshot)
            self._gpu_view.update_snapshots(snapshot)
        elif key == "disk" and isinstance(snapshot, DiskSnapshot):
            self._dashboard.update_disk(snapshot)
            self._disk_view.update_snapshot(snapshot)
        elif key == "network" and isinstance(snapshot, NetworkSnapshot):
            self._dashboard.update_network(snapshot)
            self._network_view.update_snapshot(snapshot)
        elif key == "io" and isinstance(snapshot, IOSnapshot):
            self._dashboard.update_io(snapshot)
            self._io_view.update_snapshot(snapshot)
        elif key == "pcie" and isinstance(snapshot, PCIESnapshot):
            self._dashboard.update_pcie(snapshot)
            self._pcie_view.update_snapshot(snapshot)
        elif key == "processes" and isinstance(snapshot, ProcessSnapshot):
            self._processes.update_snapshot(snapshot)
        elif key == "temperature" and isinstance(snapshot, TemperatureSensorsSnapshot):
            self._dashboard.update_temperature(snapshot)
            self._sensors_view.update_temperature(snapshot)
        elif key == "fans" and isinstance(snapshot, FanSensorsSnapshot):
            self._dashboard.update_fans(snapshot)
            self._sensors_view.update_fans(snapshot)
        elif key == "battery" and isinstance(snapshot, BatterySnapshot):
            self._dashboard.update_battery(snapshot)
            self._sensors_view.update_battery(snapshot)
        elif key == "power" and isinstance(snapshot, PowerSourcesSnapshot):
            self._dashboard.update_power(snapshot)
            self._sensors_view.update_power_sources(snapshot)
        elif key == "system" and isinstance(snapshot, SystemInfoSnapshot):
            self._dashboard.update_system(snapshot)
            self._system_view.update_snapshot(snapshot)

        self.statusBar().showMessage(f"Actualizado {key}")
