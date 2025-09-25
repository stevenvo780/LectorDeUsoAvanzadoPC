"""Ejecuta el servidor web durante unos segundos para pruebas manuales."""

from __future__ import annotations

import sys
import threading
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mission_center.web.server import create_app


def _run_server(stop_event: threading.Event) -> None:
    server = create_app(port=0)
    address = server.server_address()
    print(f"Iniciando Mission Center Web en {address} (modo temporal)")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        while not stop_event.wait(0.1):
            pass
    finally:
        server.stop()
        thread.join()
        print("Servidor detenido")


def main(duration: float = 3.0) -> None:
    stop_event = threading.Event()
    worker = threading.Thread(target=_run_server, args=(stop_event,), daemon=True)
    worker.start()
    try:
        time.sleep(duration)
    finally:
        stop_event.set()
        worker.join()


if __name__ == "__main__":
    main()
