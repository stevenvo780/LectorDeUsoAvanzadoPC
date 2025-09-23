"""Processes view replicating Mission Center lists."""

from __future__ import annotations

import datetime as dt

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHeaderView, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from mission_center_clone.models import ProcessSnapshot

_COLUMNS = [
    ("PID", 80),
    ("Nombre", 200),
    ("CPU %", 80),
    ("Memoria", 120),
    ("Lectura IO", 120),
    ("Escritura IO", 120),
    ("Usuario", 140),
    ("Estado", 100),
    ("Inicio", 160),
    ("Comando", 320),
]


def _format_bytes(num: int | None) -> str:
    if num is None:
        return "--"
    value = float(num)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if value < 1024.0:
            return f"{value:.1f} {unit}"
        value /= 1024.0
    return f"{value:.1f} PB"


class ProcessesView(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._table = QTableWidget()
        self._table.setColumnCount(len(_COLUMNS))
        self._table.setHorizontalHeaderLabels([name for name, _ in _COLUMNS])
        header = self._table.horizontalHeader()
        for index, (_, width) in enumerate(_COLUMNS):
            if width:
                header.resizeSection(index, width)
        header.setSectionResizeMode(len(_COLUMNS) - 1, QHeaderView.Stretch)
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self._table)

    def update_snapshot(self, snapshot: ProcessSnapshot) -> None:
        processes = snapshot.processes
        self._table.setRowCount(len(processes))
        for row, process in enumerate(processes):
            start_time = (
                dt.datetime.fromtimestamp(process.create_time).strftime("%H:%M:%S")
                if process.create_time
                else "--"
            )
            values = [
                str(process.pid),
                process.name,
                f"{process.cpu_percent:.1f}",
                _format_bytes(process.memory_bytes),
                _format_bytes(process.io_read_bytes),
                _format_bytes(process.io_write_bytes),
                process.username or "--",
                process.status,
                start_time,
                " ".join(process.command_line) if process.command_line else "--",
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col in {0, 2}:
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self._table.setItem(row, col, item)
