"""Web application package for Mission Center."""

from __future__ import annotations

__all__ = [
    "create_app",
]

from .server import create_app  # noqa: E402  # lazy import to avoid circular deps
