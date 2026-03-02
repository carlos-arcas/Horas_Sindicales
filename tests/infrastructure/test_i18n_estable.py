from __future__ import annotations

import json
import re
from pathlib import Path

from app.infrastructure.i18n.servicio_i18n_estable import CargadorI18nDesdeArchivos, ServicioI18nEstable


def test_t_devuelve_traduccion_con_parametros() -> None:
    servicio = ServicioI18nEstable({"es": {"ui.sync.estado.pendiente": "Pendiente {n}"}}, idioma_inicial="es")

    assert servicio.t("ui.sync.estado.pendiente", n=2) == "Pendiente 2"


def test_t_missing_key_no_revienta_y_devuelve_fallback() -> None:
    servicio = ServicioI18nEstable({"es": {}}, idioma_inicial="es")

    assert servicio.t("ui.sync.inexistente") == "[MISSING:ui.sync.inexistente]"


def test_legacy_resolver_usa_mapa_json(tmp_path: Path) -> None:
    i18n_dir = tmp_path / "configuracion" / "i18n"
    i18n_dir.mkdir(parents=True)
    (i18n_dir / "es.json").write_text(json.dumps({"ui.app.sync.sin_config": "Sin configuración"}), encoding="utf-8")
    legacy = "app/ui/controllers/sync_controller.py:88:Sin configuración"
    (i18n_dir / "_legacy_map.json").write_text(json.dumps({legacy: "ui.app.sync.sin_config"}), encoding="utf-8")

    cargador = CargadorI18nDesdeArchivos(i18n_dir)
    servicio = ServicioI18nEstable(cargador.cargar_catalogos(), mapa_legacy=cargador.cargar_mapa_legacy())

    assert servicio.t(legacy) == "Sin configuración"


def test_catalogos_nuevos_no_aceptan_patron_legacy_como_clave_final() -> None:
    patron = re.compile(r":\d+:")
    es_catalogo = json.loads(Path("configuracion/i18n/es.json").read_text(encoding="utf-8"))
    en_catalogo = json.loads(Path("configuracion/i18n/en.json").read_text(encoding="utf-8"))

    claves = list(es_catalogo.keys()) + list(en_catalogo.keys())
    assert all(not patron.search(clave) for clave in claves)
