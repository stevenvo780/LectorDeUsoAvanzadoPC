"""Global configuration values for the Mission Center application."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class UpdateIntervals:
    """Polling intervals (in milliseconds) for the data providers."""

    fast: int = 1000  # e.g. CPU, memory, processes
    medium: int = 2000  # e.g. GPU, network
    slow: int = 5000  # e.g. sensors, PCIe


@dataclass(frozen=True)
class HistoryConfig:
    """Histogram sizing for rolling windows."""

    short_window: int = 60  # seconds
    medium_window: int = 300
    long_window: int = 1800


@dataclass(frozen=True)
class SecurityConfig:
    """Security-related defaults for the Mission Center web server."""

    allowed_origins: tuple[str, ...] = ("http://127.0.0.1:8080", "http://localhost:8080")
    allow_credentials: bool = False
    basic_auth_username: str | None = None
    basic_auth_password: str | None = None
    enable_rate_limit: bool = True
    rate_limit_requests: int = 120
    rate_limit_window_seconds: int = 60


APP_NAME = "Mission Center"
APP_ID = "com.example.mission_center"
DATA_DIR = Path.home() / ".mission_center"
CONFIG = UpdateIntervals()
HISTORY = HistoryConfig()
SECURITY = SecurityConfig()
