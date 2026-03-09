from __future__ import annotations

import pytest

from tests.ui.toast_module_loader import cargar_modulo_toast_con_stubs
from tests.ui.toast_test_helpers import assert_toast_con_accion


def test_success_acepta_action_label_action_callback() -> None:
    modulo = cargar_modulo_toast_con_stubs()
    gestor = modulo.ToastManager()

    gestor.success("ok", action_label="Abrir", action_callback=lambda: None)

    assert gestor.ultima_carga is not None
    assert_toast_con_accion(gestor.ultima_carga, nivel="success", etiqueta_accion="Abrir")


def test_error_acepta_action_label_action_callback() -> None:
    modulo = cargar_modulo_toast_con_stubs()
    gestor = modulo.ToastManager()

    gestor.error("fallo", action_label="Ver", action_callback=lambda: None)

    assert gestor.ultima_carga is not None
    assert_toast_con_accion(gestor.ultima_carga, nivel="error", etiqueta_accion="Ver")


def test_success_rechaza_kwargs_desconocidos_con_value_error() -> None:
    modulo = cargar_modulo_toast_con_stubs()
    gestor = modulo.ToastManager()

    with pytest.raises(ValueError):
        gestor.success("ok", desconocido="x")


def test_error_rechaza_kwargs_desconocidos_con_value_error() -> None:
    modulo = cargar_modulo_toast_con_stubs()
    gestor = modulo.ToastManager()

    with pytest.raises(ValueError):
        gestor.error("boom", inesperado=123)


def test_success_mapea_alias_action_text_y_action() -> None:
    modulo = cargar_modulo_toast_con_stubs()
    gestor = modulo.ToastManager()

    def callback() -> None:
        return None

    gestor.success("ok", action_text="Detalle", action=callback)

    assert gestor.ultima_carga is not None
    assert_toast_con_accion(gestor.ultima_carga, nivel="success", etiqueta_accion="Detalle")
    assert gestor.ultima_carga["action_callback"] is callback
