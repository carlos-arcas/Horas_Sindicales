from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

logger = logging.getLogger(__name__)

BASE_BG = "#0f1115"
BASE_PANEL = "#171a21"
BASE_BORDER = "#2a2f3a"
TEXT_PRIMARY = "#e6e6e6"
TEXT_SECONDARY = "#b7bcc7"
ACCENT_RED = "#d0001a"


def _build_palette() -> QPalette:
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(BASE_BG))
    palette.setColor(QPalette.Base, QColor(BASE_PANEL))
    palette.setColor(QPalette.AlternateBase, QColor("#141922"))
    palette.setColor(QPalette.Text, QColor(TEXT_PRIMARY))
    palette.setColor(QPalette.WindowText, QColor(TEXT_PRIMARY))
    palette.setColor(QPalette.Button, QColor(BASE_PANEL))
    palette.setColor(QPalette.ButtonText, QColor(TEXT_PRIMARY))
    palette.setColor(QPalette.ToolTipBase, QColor(BASE_PANEL))
    palette.setColor(QPalette.ToolTipText, QColor(TEXT_PRIMARY))
    palette.setColor(QPalette.PlaceholderText, QColor(TEXT_SECONDARY))
    palette.setColor(QPalette.Highlight, QColor(ACCENT_RED))
    palette.setColor(QPalette.HighlightedText, QColor(TEXT_PRIMARY))
    return palette


def get_qss_path() -> Path:
    root = Path(__file__).resolve().parents[2]
    return root / "app" / "ui" / "styles" / "cgt_dark.qss"


def _load_qss() -> str:
    qss_path = get_qss_path()
    try:
        return qss_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        logger.warning("No se encontro el QSS en %s", qss_path)
    except OSError:
        logger.exception("No se pudo leer el QSS en %s", qss_path)
    return ""


def apply_theme(app: QApplication) -> None:
    app.setPalette(_build_palette())
    qss = _load_qss()
    if qss:
        app.setStyleSheet(qss)
