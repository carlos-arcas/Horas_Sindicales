from __future__ import annotations

from app.ui.copy_catalog import copy_text


def t(clave: str) -> str:
    return copy_text(clave)
