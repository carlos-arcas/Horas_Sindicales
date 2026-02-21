from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QApplication

_PREMIUM_QSS_PATH = Path(__file__).resolve().parents[1] / "estilos" / "cgt_premium.qss"


def build_stylesheet() -> str:
    if _PREMIUM_QSS_PATH.exists():
        return _PREMIUM_QSS_PATH.read_text(encoding="utf-8")
    return ""


def aplicar_tema(app: QApplication) -> None:
    app.setStyleSheet(build_stylesheet())
