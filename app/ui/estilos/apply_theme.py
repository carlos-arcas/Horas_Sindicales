from __future__ import annotations

from typing import Any

from app.ui.theme.cgt_theme import aplicar_tema as aplicar_tema_cgt


def aplicar_tema(app: Any) -> None:
    aplicar_tema_cgt(app)
