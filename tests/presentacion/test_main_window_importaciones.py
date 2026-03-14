from __future__ import annotations

import inspect

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


def test_importaciones_no_depende_de_globals_update_como_nucleo() -> None:
    codigo = inspect.getsource(importaciones)

    assert "globals().update" not in codigo


def test_importaciones_expone_namespaces_y_compatibilidad_publica() -> None:
    assert hasattr(importaciones, "namespace_dialogos")
    assert hasattr(importaciones, "namespace_acciones")
    assert hasattr(importaciones, "namespace_helpers")
    assert importaciones.toast_error is importaciones.namespace_acciones.toast_error
    assert importaciones.status_badge is importaciones.namespace_helpers.status_badge
