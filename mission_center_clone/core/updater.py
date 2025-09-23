"""Qt-based scheduler that polls data providers and emits snapshots."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

try:  # PySide6 is required at runtime but optional for static analysis
    from PySide6.QtCore import QObject, QTimer, Signal
except ModuleNotFoundError as exc:  # pragma: no cover - guard for type checkers
    raise RuntimeError(
        "PySide6 is required to use mission_center_clone.core.updater"
    ) from exc


class DataUpdateCoordinator(QObject):
    """Poll a set of providers on different intervals and emit their results."""

    snapshot_updated = Signal(str, object)

    def __init__(
        self,
        providers: Mapping[str, Callable[[], Any]],
        intervals: Mapping[str, int],
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._providers = dict(providers)
        self._timers: dict[str, QTimer] = {}
        for key, provider in self._providers.items():
            interval = max(250, int(intervals.get(key, 1000)))
            timer = QTimer(self)
            timer.setInterval(interval)
            timer.timeout.connect(self._make_timeout_handler(key, provider))
            timer.start()
            self._timers[key] = timer

    def _make_timeout_handler(
        self, key: str, provider: Callable[[], Any]
    ) -> Callable[[], None]:
        def _handler() -> None:
            try:
                snapshot = provider()
            except Exception as exc:  # pragma: no cover - runtime guard
                snapshot = exc
            self.snapshot_updated.emit(key, snapshot)

        return _handler

    def request_refresh(self, key: str) -> None:
        """Trigger a manual refresh for a provider."""

        provider = self._providers.get(key)
        if not provider:
            return
        self._make_timeout_handler(key, provider)()
