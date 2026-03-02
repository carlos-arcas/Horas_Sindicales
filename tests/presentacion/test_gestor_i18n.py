from __future__ import annotations

import logging

from infraestructura.i18n.proveedor_traducciones import ProveedorTraducciones
from presentacion.i18n.gestor_i18n import GestorI18N, build_legacy_alias


class _ProveedorFake:
    def __init__(self, catalogo: dict[str, str]) -> None:
        self._catalogo = catalogo
        self.idioma_actual = "es"

    def cambiar_idioma(self, idioma: str) -> str:
        self.idioma_actual = idioma
        return idioma

    def traducir(self, clave: str, **kwargs: object) -> str:
        plantilla = self._catalogo.get(clave)
        if plantilla is None:
            return f"[i18n:{clave}]"
        return plantilla.format(**kwargs) if kwargs else plantilla


def test_cambio_dinamico_de_idioma_en_runtime() -> None:
    gestor = GestorI18N(ProveedorTraducciones("es"))

    gestor.set_idioma("en")

    assert gestor.tr("splash_window.titulo") == "Starting Horas Sindicales…"


def test_t_resuelve_por_key_semantica() -> None:
    gestor = GestorI18N(_ProveedorFake({"sync.titulo": "Sincronización"}), aliases_legacy={})

    assert gestor.t("sync.titulo") == "Sincronización"


def test_t_usa_fallback_y_loggea_warning(caplog) -> None:
    gestor = GestorI18N(_ProveedorFake({}), aliases_legacy={})

    with caplog.at_level(logging.WARNING):
        texto = gestor.t("sync.inexistente", fallback="Texto {name}", name="ok")

    assert texto == "Texto ok"
    assert caplog.records[-1].msg == "i18n_missing_key"


def test_t_resuelve_alias_legacy_sin_linea() -> None:
    ruta = "app/ui/controllers/sync_controller.py"
    texto = "Sin plan"
    alias = build_legacy_alias(ruta, texto)
    aliases = {
        alias: {
            "ruta": ruta,
            "texto": texto,
            "key_semantica": "sync.sin_plan_titulo",
        }
    }
    gestor = GestorI18N(_ProveedorFake({"sync.sin_plan_titulo": "Sin plan"}), aliases_legacy=aliases)

    assert gestor.t(f"{ruta}:999:{texto}") == "Sin plan"


def test_t_devuelve_marcador_y_log_error_si_no_hay_resolucion(caplog) -> None:
    gestor = GestorI18N(_ProveedorFake({}), aliases_legacy={})

    with caplog.at_level(logging.ERROR):
        texto = gestor.t("app/ui/controllers/sync_controller.py:1:Texto")

    assert texto == "[i18n:app/ui/controllers/sync_controller.py:1:Texto]"
    assert caplog.records[-1].msg == "i18n_missing_key_unresolved"
