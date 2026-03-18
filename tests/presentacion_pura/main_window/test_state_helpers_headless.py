from __future__ import annotations

from importlib import import_module

import pytest

from app.application.modo_solo_lectura import crear_estado_modo_solo_lectura
from app.ui.copy_catalog import copy_text

pytestmark = pytest.mark.headless_safe


class _ControlStub:
    def __init__(self) -> None:
        self.enabled: bool | None = None
        self.text: str = ""

    def setEnabled(self, value: bool) -> None:
        self.enabled = value

    def setText(self, value: str) -> None:
        self.text = value


class _WindowStub:
    def __init__(self) -> None:
        self._blocking_errors = {}
        self._pending_solicitudes = [object()]
        self._pending_conflict_rows = set()
        self._pending_view_all = False
        self._sync_in_progress = False
        self._pending_otras_delegadas = [object()]
        self._historico_ids_seleccionados = {99}
        self._estado_modo_solo_lectura = crear_estado_modo_solo_lectura(lambda: False)

        self.agregar_button = _ControlStub()
        self.insertar_sin_pdf_button = _ControlStub()
        self.confirmar_button = _ControlStub()
        self.eliminar_huerfana_button = _ControlStub()
        self.add_persona_button = _ControlStub()
        self.edit_persona_button = _ControlStub()
        self.delete_persona_button = _ControlStub()
        self.edit_grupo_button = _ControlStub()
        self.editar_pdf_button = _ControlStub()
        self.opciones_button = _ControlStub()
        self.config_sync_button = _ControlStub()
        self.sync_button = _ControlStub()
        self.confirm_sync_button = _ControlStub()
        self.retry_failed_button = _ControlStub()
        self.accion_menu_cargar_demo = _ControlStub()
        self.eliminar_button = _ControlStub()
        self.eliminar_pendiente_button = _ControlStub()
        self.generar_pdf_button = _ControlStub()
        self.clear_button = _ControlStub()

        self.status_panel_actualizado = 0

    def _current_persona(self) -> object:
        return object()

    def _validate_solicitud_form(self) -> tuple[bool, str]:
        return True, ""

    def _selected_pending_solicitudes(self) -> list[object]:
        return [object()]

    def _selected_historico_solicitudes(self) -> list[object]:
        return []

    def _update_solicitudes_status_panel(self) -> None:
        self.status_panel_actualizado += 1


def _load_state_helpers_module():
    return import_module("app.ui.vistas.main_window.state_helpers")


def test_resolve_active_delegada_id_prioriza_preferido_valido() -> None:
    module = _load_state_helpers_module()
    assert module.resolve_active_delegada_id([10, 20, 30], "20") == 20


def test_resolve_active_delegada_id_usa_primera_si_preferido_no_valido() -> None:
    module = _load_state_helpers_module()
    assert module.resolve_active_delegada_id([10, 20, 30], "999") == 10


def test_resolve_active_delegada_id_none_si_no_hay_ids() -> None:
    module = _load_state_helpers_module()
    assert module.resolve_active_delegada_id([], "20") is None


def test_update_action_state_aplica_fuente_unica_de_estado_en_widgets() -> None:
    module = _load_state_helpers_module()
    window = _WindowStub()

    module.update_action_state(window)

    assert window.agregar_button.enabled is True
    assert window.insertar_sin_pdf_button.enabled is True
    assert window.confirmar_button.enabled is True
    assert window.eliminar_button.enabled is True
    assert window.eliminar_button.text == copy_text("ui.historico.eliminar_boton").format(n=1)
    assert window.generar_pdf_button.enabled is True
    assert window.generar_pdf_button.text == copy_text("ui.historico.exportar_pdf_boton").format(n=1)
    assert window.opciones_button.enabled is True
    assert window.clear_button.enabled is True
    assert window.status_panel_actualizado == 1


def test_update_action_state_tolera_boton_historico_sin_set_text() -> None:
    module = _load_state_helpers_module()
    window = _WindowStub()
    window.generar_pdf_button = object()

    module.update_action_state(window)

    assert window.eliminar_button.text == copy_text("ui.historico.eliminar_boton").format(n=1)
    assert window.status_panel_actualizado == 1
