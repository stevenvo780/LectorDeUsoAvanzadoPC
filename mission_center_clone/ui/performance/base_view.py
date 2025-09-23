"""Shared helpers for performance subviews."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class PerformanceViewBase(QWidget):
    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        self._title = QLabel(title)
        self._title.setProperty("class", "performance-title")
        self._title.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self._summary = QLabel("--")
        self._summary.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self._summary.setWordWrap(True)
        layout.addWidget(self._title)
        layout.addWidget(self._summary)
        self._content_layout = QVBoxLayout()
        self._content_layout.setSpacing(16)
        layout.addLayout(self._content_layout)
        layout.addStretch(1)

    def update_summary(self, text: str) -> None:
        self._summary.setText(text)

    def add_widget(self, widget: QWidget) -> None:
        """Expose a hook for subclasses to append charts or tables."""

        self._content_layout.addWidget(widget)
