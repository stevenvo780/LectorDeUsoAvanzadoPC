"""Smoke test para el servidor web de Mission Center."""

from __future__ import annotations

import json
import sys
import threading
import time
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mission_center.web.server import create_app


def fetch_json(url: str) -> dict[str, object]:
    with urllib.request.urlopen(url) as response:  # nosec - uso local en smoke test
        payload = response.read().decode("utf-8")
    return json.loads(payload)


def run_smoke() -> None:
    server = create_app(port=0)
    address = server.server_address()
    print(f"Iniciando servidor en {address}")

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        time.sleep(0.5)  # pequeño margen para que el hilo arranque
        current = fetch_json(f"{address}/api/current")
        history = fetch_json(f"{address}/api/history")
        assert "cpu" in current, "Snapshot sin datos de CPU"
        assert "memory" in current, "Snapshot sin datos de memoria"
        assert "cpu" in history, "Histórico sin serie de CPU"
        print("SMOKE_OK", {
            "cpu_usage": current.get("cpu", {}).get("usage_percent"),
            "history_points": len(history.get("cpu", [])),
        })
    finally:
        server.stop()
        thread.join()

if __name__ == "__main__":
    run_smoke()
