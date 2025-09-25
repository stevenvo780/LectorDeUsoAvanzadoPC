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
        try:
            html = template_renderer.render("index_new.html")
            content = html.encode("utf-8")
        except Exception as template_error:
            print(f"Template rendering error: {template_error}")
            content = None

        if content is None:
            fallback_files = ["index_clean.html", "index.html"]
            for candidate in fallback_files:
                candidate_path = TEMPLATES_DIR / candidate
                if candidate_path.exists():
                    try:
                        content = candidate_path.read_text(encoding="utf-8").encode("utf-8")
                        break
                    except Exception as read_error:
                        print(f"Error loading fallback template {candidate}: {read_error}")
                        continue

        if content is None:
            content = b"<html><body><h1>Mission Center</h1><p>Template error</p></body></html>"
        
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
        
        # Mejorar manejo de puertos ocupados
        max_attempts = 10
        for attempt in range(max_attempts):
            try:
                self._httpd = ThreadingHTTPServer((host, port + attempt), handler)
                self.host = host
                self.port = port + attempt
                break
            except OSError as e:
                if e.errno == 98:  # Address already in use
                    if attempt == max_attempts - 1:
                        raise Exception(f"No se pudo encontrar puerto disponible después de {max_attempts} intentos")
                    continue
                else:
                    raise

    def serve_forever(self) -> None:
        try:
            self._httpd.serve_forever()
        finally:
            self.stop()

    def stop(self) -> None:
        try:
            if hasattr(self, '_httpd') and self._httpd:
                self._httpd.shutdown()
        except Exception as e:
            print(f"Warning: Error al detener servidor: {e}")
        finally:
            try:
                if hasattr(self, '_httpd') and self._httpd:
                    self._httpd.server_close()
            except Exception as e:
                print(f"Warning: Error al cerrar socket: {e}")
            finally:
                if hasattr(self, '_collector') and self._collector:
                    self._collector.stop()

    def server_address(self) -> str:
        host, port = self._httpd.server_address
        return f"http://{host}:{port}"


def create_app(host: str = "127.0.0.1", port: int = 8080) -> MissionCenterServer:
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
