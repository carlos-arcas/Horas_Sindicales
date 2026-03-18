from __future__ import annotations

from importlib import import_module

import pytest

from app.application.modo_solo_lectura import crear_estado_modo_solo_lectura
from app.ui.copy_catalog import copy_text
from app.ui.vistas.main_window.politica_solo_lectura import (
    ACCIONES_MUTANTES_AUDITADAS_UI,
    DescriptorAccionMutante,
    NOMBRES_CONTROLES_MUTANTES_UI,
    exportar_inventario_acciones_mutantes,
    resolver_control_mutante,
)
from tests.presentacion_pura.main_window.contrato_inventario_solo_lectura import (
    exportar_contrato_inventario_mutante,
    validar_contrato_inventario_con_fuentes,
    validar_inventario_runtime_mutante,
)

pytestmark = pytest.mark.headless_safe


class _ControlStub:
    def __init__(self, *, object_name: str = "") -> None:
        self.enabled: bool | None = None
        self.tooltip = ""
        self.text = ""
        self._object_name = object_name

    def objectName(self) -> str:
        return self._object_name

    def setEnabled(self, value: bool) -> None:
        self.enabled = value

    def setToolTip(self, value: str) -> None:
        self.tooltip = value

    def setText(self, value: str) -> None:
        self.text = value


class _WindowStub:
    def __init__(self, *, solo_lectura: bool) -> None:
        self._blocking_errors = {}
        self._pending_solicitudes = [object()]
        self._pending_conflict_rows = set()
        self._pending_view_all = False
        self._sync_in_progress = False
        self._pending_otras_delegadas = []
        self._historico_ids_seleccionados = {7}
        self._estado_modo_solo_lectura = crear_estado_modo_solo_lectura(
            lambda: solo_lectura
        )
        self._children: list[object] = []

        for nombre in (
            "agregar_button",
            "insertar_sin_pdf_button",
            "confirmar_button",
            "eliminar_pendiente_button",
            "eliminar_huerfana_button",
            "add_persona_button",
            "edit_persona_button",
            "delete_persona_button",
            "edit_grupo_button",
            "editar_pdf_button",
            "opciones_button",
            "config_sync_button",
            "sync_button",
            "confirm_sync_button",
            "retry_failed_button",
            "accion_menu_cargar_demo",
            "eliminar_button",
            "generar_pdf_button",
            "clear_button",
        ):
            control = _ControlStub(object_name=nombre)
            setattr(self, nombre, control)
            self._children.append(control)

        self.status_panel_actualizado = 0

    def findChildren(
        self, _tipo: object = object, object_name: str | None = None
    ) -> list[object]:
        if object_name is None:
            return list(self._children)
        return [
            child
            for child in self._children
            if getattr(child, "objectName", lambda: "")() == object_name
        ]

    def _current_persona(self) -> object:
        return object()

    def _validate_solicitud_form(self) -> tuple[bool, str]:
        return True, ""

    def _selected_pending_solicitudes(self) -> list[object]:
        return [object()]

    def _selected_historico_solicitudes(self) -> list[object]:
        return [object()]

    def _update_solicitudes_status_panel(self) -> None:
        self.status_panel_actualizado += 1


def test_update_action_state_deshabilita_acciones_mutantes_en_modo_solo_lectura() -> (
    None
):
    modulo = import_module("app.ui.vistas.main_window.state_helpers")
    window = _WindowStub(solo_lectura=True)

    modulo.update_action_state(window)

    tooltip = copy_text("ui.read_only.tooltip_mutacion_bloqueada")
    for nombre in NOMBRES_CONTROLES_MUTANTES_UI:
        control = getattr(window, nombre)
        assert control.enabled is False, nombre
        assert control.tooltip == tooltip, nombre
    assert window.clear_button.enabled is True
    assert window.status_panel_actualizado == 1


def test_update_action_state_restablece_estado_normal_fuera_de_solo_lectura() -> None:
    modulo = import_module("app.ui.vistas.main_window.state_helpers")
    window = _WindowStub(solo_lectura=False)

    modulo.update_action_state(window)

    assert window.agregar_button.enabled is True
    assert window.insertar_sin_pdf_button.enabled is True
    assert window.confirmar_button.enabled is True
    assert window.sync_button.enabled is None
    assert window.config_sync_button.enabled is None
    assert window.retry_failed_button.enabled is None
    assert window.eliminar_button.enabled is True
    assert window.generar_pdf_button.enabled is True
    assert window.add_persona_button.enabled is True
    assert window.opciones_button.enabled is True
    assert window.agregar_button.tooltip == ""


def test_inventario_acciones_mutantes_ui_queda_centralizado_y_tipado() -> None:
    assert ACCIONES_MUTANTES_AUDITADAS_UI
    assert all(
        isinstance(descriptor, DescriptorAccionMutante)
        for descriptor in ACCIONES_MUTANTES_AUDITADAS_UI
    )
    assert NOMBRES_CONTROLES_MUTANTES_UI == tuple(
        descriptor.object_name for descriptor in ACCIONES_MUTANTES_AUDITADAS_UI
    )
    assert validar_inventario_runtime_mutante() == []
    assert validar_contrato_inventario_con_fuentes() == []
    assert exportar_inventario_acciones_mutantes()["agregar_button"] == {
        "tipo_control": "widget",
        "pantalla": "solicitudes",
        "accion": "agregar_pendiente",
    }
    assert exportar_contrato_inventario_mutante()["agregar_button"] == {
        "tipo_control": "widget",
        "ruta_origen": "app/ui/vistas/builders/formulario_solicitud/builders_solicitud.py",
    }


def test_resolver_control_mutante_prioriza_object_name_sobre_atributo() -> None:
    descriptor = DescriptorAccionMutante(
        "agregar_button",
        "widget",
        "solicitudes",
        "agregar_pendiente",
    )
    window = _WindowStub(solo_lectura=False)
    window.agregar_button = _ControlStub(object_name="nombre_inestable")

    control_real = resolver_control_mutante(window, descriptor)

    assert control_real is not None
    assert control_real.objectName() == "agregar_button"


def test_update_action_state_falla_si_falta_estado_modo_solo_lectura() -> None:
    modulo = import_module("app.ui.vistas.main_window.state_helpers")
    window = _WindowStub(solo_lectura=False)
    delattr(window, "_estado_modo_solo_lectura")

    with pytest.raises(TypeError, match="_estado_modo_solo_lectura"):
        modulo.update_action_state(window)
