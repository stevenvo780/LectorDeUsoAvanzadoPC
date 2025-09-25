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


APP_NAME = "Mission Center"
APP_ID = "com.example.mission_center"
DATA_DIR = Path.home() / ".mission_center"
CONFIG = UpdateIntervals()
HISTORY = HistoryConfig()
