from __future__ import annotations

from importlib import import_module

from app.ui.copy_catalog import copy_text
from app.ui.vistas.main_window.politica_solo_lectura import (
    ACCIONES_MUTANTES_AUDITADAS_UI,
    DescriptorAccionMutante,
    NOMBRES_CONTROLES_MUTANTES_UI,
    exportar_inventario_acciones_mutantes,
)


class _ControlStub:
    def __init__(self) -> None:
        self.enabled: bool | None = None
        self.tooltip = ""
        self.text = ""

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
        self._proveedor_ui_solo_lectura = lambda: solo_lectura

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
            setattr(self, nombre, _ControlStub())

        self.status_panel_actualizado = 0

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
    assert window.sync_button.enabled is True
    assert window.config_sync_button.enabled is True
    assert window.retry_failed_button.enabled is False
    assert window.eliminar_button.enabled is True
    assert window.generar_pdf_button.enabled is True
    assert window.add_persona_button.enabled is True
    assert window.opciones_button.enabled is True
    assert window.agregar_button.tooltip == ""


def test_inventario_acciones_mutantes_ui_queda_centralizado_en_fuente_unica() -> None:
    assert ACCIONES_MUTANTES_AUDITADAS_UI
    assert all(
        isinstance(descriptor, DescriptorAccionMutante)
        for descriptor in ACCIONES_MUTANTES_AUDITADAS_UI
    )
    assert NOMBRES_CONTROLES_MUTANTES_UI == tuple(
        descriptor.nombre_control for descriptor in ACCIONES_MUTANTES_AUDITADAS_UI
    )
    assert exportar_inventario_acciones_mutantes() == {
        "agregar_button": {"pantalla": "solicitudes", "accion": "agregar_pendiente"},
        "insertar_sin_pdf_button": {
            "pantalla": "solicitudes",
            "accion": "confirmar_sin_pdf",
        },
        "confirmar_button": {"pantalla": "solicitudes", "accion": "confirmar_con_pdf"},
        "eliminar_pendiente_button": {
            "pantalla": "solicitudes",
            "accion": "eliminar_solicitud_pendiente",
        },
        "eliminar_huerfana_button": {
            "pantalla": "solicitudes",
            "accion": "eliminar_solicitud_huerfana",
        },
        "add_persona_button": {"pantalla": "configuracion", "accion": "crear_persona"},
        "edit_persona_button": {
            "pantalla": "configuracion",
            "accion": "editar_persona",
        },
        "delete_persona_button": {
            "pantalla": "configuracion",
            "accion": "desactivar_persona",
        },
        "edit_grupo_button": {
            "pantalla": "configuracion",
            "accion": "actualizar_configuracion_grupo",
        },
        "editar_pdf_button": {
            "pantalla": "configuracion",
            "accion": "actualizar_configuracion_pdf",
        },
        "opciones_button": {
            "pantalla": "sincronizacion",
            "accion": "actualizar_configuracion_sync",
        },
        "config_sync_button": {
            "pantalla": "sincronizacion",
            "accion": "sincronizar_desde_configuracion",
        },
        "sync_button": {"pantalla": "sincronizacion", "accion": "sincronizar_ahora"},
        "confirm_sync_button": {
            "pantalla": "sincronizacion",
            "accion": "confirmar_sincronizacion",
        },
        "retry_failed_button": {
            "pantalla": "sincronizacion",
            "accion": "reintentar_sincronizacion_fallida",
        },
        "accion_menu_cargar_demo": {
            "pantalla": "menu_ayuda",
            "accion": "cargar_datos_demo",
        },
        "eliminar_button": {
            "pantalla": "historico",
            "accion": "eliminar_solicitud_historica",
        },
        "generar_pdf_button": {
            "pantalla": "historico",
            "accion": "exportar_historico_pdf",
        },
    }


def test_update_action_state_falla_si_falta_proveedor_ui_solo_lectura() -> None:
    modulo = import_module("app.ui.vistas.main_window.state_helpers")
    window = _WindowStub(solo_lectura=False)
    delattr(window, "_proveedor_ui_solo_lectura")

    try:
        modulo.update_action_state(window)
    except TypeError as exc:
        assert "_proveedor_ui_solo_lectura" in str(exc)
    else:  # pragma: no cover - guardarraíl explícito
        raise AssertionError(
            "Se esperaba TypeError cuando falta el proveedor UI de solo lectura"
        )
