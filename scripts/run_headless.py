import os
import sys
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# Asegurar path del proyecto
ROOT = os.path.dirname(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from mission_center_clone.ui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    win = MainWindow()
    # No show(); offscreen
    QTimer.singleShot(3000, app.quit)  # 3s loop
    t0 = time.time()
    rc = app.exec()
    print(f"HEADLESS_OK dt={time.time()-t0:.2f}s rc={rc}")
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
