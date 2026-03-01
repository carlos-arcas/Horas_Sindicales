from __future__ import annotations

from app.ui.wizard_bienvenida.paginas.pagina_base import PaginaTexto
from presentacion.i18n import I18nManager


class PaginaBasicos(PaginaTexto):
    def __init__(self, i18n: I18nManager) -> None:
        super().__init__(i18n, "wizard_paso_2", "wizard_conceptos_texto")
