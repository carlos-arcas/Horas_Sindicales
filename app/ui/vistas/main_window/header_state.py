from __future__ import annotations

from app.ui.copy_catalog import copy_text


SECTION_TITLE_KEYS_BY_SIDEBAR_INDEX = {
    0: "ui.sync.tab_sincronizacion",
    1: "solicitudes.section_title",
    2: "ui.historico.tab",
    3: "ui.sync.configuracion",
}
DEFAULT_SECTION_TITLE_KEY = "solicitudes.section_title"


def resolve_section_title(sidebar_index: int) -> str:
    """Devuelve el título visible del header externo para una sección del shell."""

    title_key = SECTION_TITLE_KEYS_BY_SIDEBAR_INDEX.get(sidebar_index, DEFAULT_SECTION_TITLE_KEY)
    return copy_text(title_key)


def resolve_sidebar_tab_index(sidebar_index: int) -> int | None:
    sidebar_to_tab_index = {
        0: None,
        1: 0,
        2: 1,
        3: 2,
    }
    return sidebar_to_tab_index.get(sidebar_index)
