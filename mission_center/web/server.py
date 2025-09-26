"""HTTP server exposing the Mission Center web dashboard."""

from __future__ import annotations

import base64
import json
import logging
import threading
import time
from collections import deque
from functools import partial
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, ClassVar, Deque, Optional

from .collector import DataCollector, collector
from .template_renderer import SimpleTemplateRenderer
from mission_center.core.config import SECURITY

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

# Initialize template renderer
template_renderer = SimpleTemplateRenderer(TEMPLATES_DIR)
logger = logging.getLogger(__name__)


class MissionCenterRequestHandler(SimpleHTTPRequestHandler):
    """Custom handler that serves static assets and JSON APIs."""

    server_version: ClassVar[str] = "MissionCenterWeb/1.0"
    _rate_lock: ClassVar[threading.Lock] = threading.Lock()
    _request_log: ClassVar[dict[str, Deque[float]]] = {}

    def __init__(
        self,
        *args: Any,
        data_collector: DataCollector,
        security_config = SECURITY,
        **kwargs: Any,
    ) -> None:
        self._collector = data_collector
        self._security = security_config
        self._response_origin: Optional[str] = None
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    def do_GET(self) -> None:  # noqa: N802
        self._response_origin = None
        if self.path in {"/", "/index.html"}:
            self._send_index()
            return
        if self.path == "/api/current":
            if not self._prepare_api_request():
                return
            self._send_json(self._collector.snapshot())
            return
        if self.path == "/api/history":
            if not self._prepare_api_request():
                return
            self._send_json(self._collector.history())
            return
        super().do_GET()

    def do_OPTIONS(self) -> None:  # noqa: N802
        allowed, origin = self._resolve_origin()
        if not allowed:
            return
        self._response_origin = origin
        self.send_response(HTTPStatus.NO_CONTENT)
        self._apply_cors_headers(origin)
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
        self.send_header("Access-Control-Max-Age", "600")
        self.end_headers()

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
        self._apply_cors_headers(self._response_origin)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _prepare_api_request(self) -> bool:
        allowed, origin = self._resolve_origin()
        if not allowed:
            return False
        self._response_origin = origin
        if not self._check_basic_auth():
            self._require_auth()
            return False
        if not self._enforce_rate_limit():
            return False
        return True

    def _resolve_origin(self) -> tuple[bool, Optional[str]]:
        origin = self.headers.get("Origin")
        allowed = self._security.allowed_origins
        if origin:
            if "*" in allowed or origin in allowed:
                if "*" in allowed and not self._security.allow_credentials:
                    return True, "*"
                return True, origin
            self._respond_forbidden("Origin no autorizado")
            return False, None
        if "*" in allowed and not self._security.allow_credentials:
            return True, "*"
        return True, None

    def _apply_cors_headers(self, origin: Optional[str]) -> None:
        allowed = self._security.allowed_origins
        header_value: Optional[str] = origin
        if origin is None and "*" in allowed and not self._security.allow_credentials:
            header_value = "*"
        if header_value:
            self.send_header("Access-Control-Allow-Origin", header_value)
        if self._security.allow_credentials and header_value and header_value != "*":
            self.send_header("Access-Control-Allow-Credentials", "true")
        self.send_header("Vary", "Origin")

    def _check_basic_auth(self) -> bool:
        username = self._security.basic_auth_username
        password = self._security.basic_auth_password
        if not username or not password:
            return True
        header = self.headers.get("Authorization")
        if not header or not header.startswith("Basic "):
            return False
        token = header.split(" ", 1)[1]
        try:
            decoded = base64.b64decode(token).decode("utf-8")
        except Exception:
            return False
        provided_user, _, provided_pass = decoded.partition(":")
        return provided_user == username and provided_pass == password

    def _require_auth(self) -> None:
        self.send_response(HTTPStatus.UNAUTHORIZED)
        self._apply_cors_headers(self._response_origin)
        self.send_header("WWW-Authenticate", 'Basic realm="Mission Center", charset="UTF-8"')
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _enforce_rate_limit(self) -> bool:
        if not self._security.enable_rate_limit:
            return True
        client_ip = self.client_address[0]
        now = time.monotonic()
        window = max(1, self._security.rate_limit_window_seconds)
        max_requests = max(1, self._security.rate_limit_requests)
        with self._rate_lock:
            bucket = self._request_log.setdefault(client_ip, deque())
            while bucket and now - bucket[0] > window:
                bucket.popleft()
            if len(bucket) >= max_requests:
                self._too_many_requests()
                return False
            bucket.append(now)
        return True

    def _too_many_requests(self) -> None:
        retry_after = str(self._security.rate_limit_window_seconds)
        body = json.dumps({"error": "rate_limit", "retry_after": retry_after}).encode("utf-8")
        logger.warning("Rate limit excedido para %s", self.client_address[0])
        self.send_response(HTTPStatus.TOO_MANY_REQUESTS)
        self._apply_cors_headers(self._response_origin)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Retry-After", retry_after)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _respond_forbidden(self, message: str) -> None:
        logger.warning("Solicitud bloqueada por CORS desde %s: %s", self.client_address[0], message)
        body = json.dumps({"error": "forbidden", "message": message}).encode("utf-8")
        self.send_response(HTTPStatus.FORBIDDEN)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class MissionCenterServer:
    """Wraps the HTTP server and manages the shared data collector."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8080) -> None:
        self._collector = collector
        self._collector.start()
        handler = partial(
            MissionCenterRequestHandler,
            data_collector=self._collector,
            security_config=SECURITY,
        )

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
