from __future__ import annotations

import pytest

from app.ui.vistas.main_window import importaciones


def test_cargar_importacion_grupo_aplica_fallback_cuando_falta_qt() -> None:
    def _carga_fallida() -> dict[str, object]:
        raise ImportError("No module named PySide6", name="PySide6")

    fallback = {"valor": object()}
    resultado = importaciones._cargar_importacion_grupo(_carga_fallida, fallback)

    assert resultado is fallback


def test_cargar_importacion_grupo_no_oculta_error_no_qt() -> None:
    def _carga_fallida() -> dict[str, object]:
        raise ImportError("fallo real de import", name="app.ui.modulo_roto")

    with pytest.raises(ImportError, match="fallo real de import"):
        importaciones._cargar_importacion_grupo(_carga_fallida, {"valor": object()})


def test_importaciones_segmenta_carga_por_responsabilidad() -> None:
    for nombre_loader in (
        "_cargar_grupo_dialogos_y_controllers",
        "_cargar_grupo_acciones_y_estado",
        "_cargar_grupo_helpers_builders_y_sync",
    ):
        assert callable(getattr(importaciones, nombre_loader))
