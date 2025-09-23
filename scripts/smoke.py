import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

# Asegura que la raíz del repo esté en sys.path para importar el paquete
ROOT = os.path.dirname(os.path.dirname(__file__))
if ROOT not in sys.path:
	sys.path.insert(0, ROOT)

# Import main window to catch import errors
from mission_center_clone.ui.main_window import MainWindow

app = QApplication(sys.argv)
# Avoid showing the window in smoke test
win = MainWindow()
# Hook minimal interactions to ensure widgets build
assert win.centralWidget() is not None
# Close immediately
win.close()
print("SMOKE_OK")
