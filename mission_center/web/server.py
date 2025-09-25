"""HTTP server exposing the Mission Center web dashboard."""

from __future__ import annotations

import json
from functools import partial
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, ClassVar

from .collector import DataCollector, collector
from .template_renderer import SimpleTemplateRenderer

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

# Initialize template renderer
template_renderer = SimpleTemplateRenderer(TEMPLATES_DIR)


class MissionCenterRequestHandler(SimpleHTTPRequestHandler):
    """Custom handler that serves static assets and JSON APIs."""

    server_version: ClassVar[str] = "MissionCenterWeb/1.0"

    def __init__(self, *args: Any, data_collector: DataCollector, **kwargs: Any) -> None:
        self._collector = data_collector
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    def do_GET(self) -> None:  # noqa: N802
        if self.path in {"/", "/index.html"}:
            self._send_index()
            return
        if self.path == "/api/current":
            self._send_json(self._collector.snapshot())
            return
        if self.path == "/api/history":
            self._send_json(self._collector.history())
            return
        super().do_GET()

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003 - parity with BaseHTTPRequestHandler
        # Silence default stdout logging to keep console clean.
        return

    def _send_index(self) -> None:
        # Try new template system first, fallback to old system
        try:
            rendered_html = template_renderer.render("index_new.html")
            content = rendered_html.encode("utf-8")
        except FileNotFoundError:
            # Fallback to original index.html
            index_path = TEMPLATES_DIR / "index.html"
            content = index_path.read_text(encoding="utf-8").encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _send_json(self, payload: Any) -> None:
        body = json.dumps(payload or {}).encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class MissionCenterServer:
    """Wraps the HTTP server and manages the shared data collector."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8080) -> None:
        self._collector = collector
        self._collector.start()
        handler = partial(MissionCenterRequestHandler, data_collector=self._collector)
        self._httpd = ThreadingHTTPServer((host, port), handler)
        self.host = host
        self.port = port

    def serve_forever(self) -> None:
        try:
            self._httpd.serve_forever()
        finally:
            self.stop()

    def stop(self) -> None:
        try:
            self._httpd.shutdown()
        finally:
            self._httpd.server_close()
            self._collector.stop()

    def server_address(self) -> str:
        host, port = self._httpd.server_address
        return f"http://{host}:{port}"


def create_app(host: str = "127.0.0.1", port: int = 8081) -> MissionCenterServer:
    """Factory helper used by CLI scripts and tests."""

    return MissionCenterServer(host=host, port=port)


def main() -> None:
    server = create_app()
    address = server.server_address()
    print("🚀 Mission Center Web UI")
    print(f"🌐 Servidor disponible en {address}")
    print("⏹️  Presiona Ctrl+C para detener")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Deteniendo servidor...")
        server.stop()


if __name__ == "__main__":
    main()
