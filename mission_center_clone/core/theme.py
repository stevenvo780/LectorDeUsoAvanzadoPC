"""Theme helpers and style sheets."""

from __future__ import annotations

from pathlib import Path

# Basic palette placeholders inspired by the Windows Mission Center look.
PRIMARY_COLOR = "#2563eb"
BACKGROUND_COLOR = "#0f172a"
CARD_COLOR = "#111827"
CARD_BORDER_RADIUS = 12
FONT_FAMILY = "Segoe UI, Noto Sans, sans-serif"


def load_stylesheet() -> str:
    """Return the base Qt stylesheet for the application."""

    return f"""
        QMainWindow {{
            background-color: {BACKGROUND_COLOR};
            color: white;
        }}
        QWidget[objectName="ResourceCard"] {{
            background-color: {CARD_COLOR};
            border-radius: {CARD_BORDER_RADIUS}px;
        }}
        QLabel {{
            font-family: {FONT_FAMILY};
        }}
        QListWidget {{
            background-color: transparent;
            border: none;
        }}
        QListWidget::item {{
            padding: 12px;
        }}
        QListWidget::item:selected {{
            background-color: {PRIMARY_COLOR};
        }}
    """.strip()


def resource_icon(name: str) -> Path:
    """Build a path to an icon resource."""

    return Path(__file__).resolve().parent.parent / "resources" / "icons" / f"{name}.svg"
