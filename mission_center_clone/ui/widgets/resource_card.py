"""Simple card widget to display a key metric."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class ResourceCard(QWidget):
    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("ResourceCard")
        self._title = QLabel(title)
        self._title.setProperty("class", "card-title")
        self._title.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self._value = QLabel("--")
        self._value.setProperty("class", "card-value")
        self._value.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self._value.setWordWrap(True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.addWidget(self._title)
        layout.addWidget(self._value)
        layout.addStretch(1)

    def update_value(self, text: str) -> None:
        self._value.setText(text)
