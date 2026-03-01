from __future__ import annotations

from app.ui.copy_catalog import copy_text


def resolve_section_title(sidebar_index: int) -> str:
    """Devuelve el título visible del header externo para una sección del shell."""

    titles_by_sidebar_index = {
        0: "Sincronización",
        1: copy_text("solicitudes.section_title"),
        2: copy_text("ui.historico.tab"),
        3: copy_text("ui.sync.configuracion"),
    }
    return titles_by_sidebar_index.get(sidebar_index, copy_text("solicitudes.section_title"))


def resolve_sidebar_tab_index(sidebar_index: int) -> int | None:
    sidebar_to_tab_index = {
        0: None,
        1: 0,
        2: 1,
        3: 2,
    }
    return sidebar_to_tab_index.get(sidebar_index)
