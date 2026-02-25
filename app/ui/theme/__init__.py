from __future__ import annotations

from typing import Any

__all__ = ["aplicar_tema", "build_stylesheet"]


def build_stylesheet() -> str:
    from app.ui.theme.cgt_theme import build_stylesheet as _build_stylesheet

    return _build_stylesheet()


def aplicar_tema(app: Any) -> None:
    from app.ui.theme.cgt_theme import aplicar_tema as _aplicar_tema

    _aplicar_tema(app)
