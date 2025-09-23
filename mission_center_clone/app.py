"""Application entry point."""

from __future__ import annotations

import os
import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from mission_center_clone.core import APP_NAME
from mission_center_clone.ui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    window = MainWindow()
    window.show()
    # Permite ejecuciones headless temporizadas (por ejemplo, CI o primera validación)
    exit_ms = os.environ.get("MISSION_CENTER_HEADLESS_EXIT_MS")
    if exit_ms and exit_ms.isdigit():
        QTimer.singleShot(int(exit_ms), app.quit)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
