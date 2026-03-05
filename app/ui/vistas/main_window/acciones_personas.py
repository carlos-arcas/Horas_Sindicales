from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.application.claves_configuracion import (
    CLAVE_CONTEXTO_DELEGADA_ACTIVA,
    CLAVE_CONTEXTO_DELEGADA_SELECCIONADA_ID,
    CLAVE_HISTORICO_DELEGADA,
)
from app.domain.services import BusinessRuleError, ValidacionError
from app.ui.copy_catalog import copy_text
from app.ui.person_dialog import PersonaDialog
from app.ui.vistas.personas_presenter import PersonaOption, PersonasLoadInput, build_personas_load_output

try:
    from PySide6.QtCore import QDate, QTime
    from PySide6.QtWidgets import QMessageBox
except Exception:  # pragma: no cover - habilita import en entornos CI sin Qt
    QDate = QTime = QMessageBox = object

if TYPE_CHECKING:
    from app.application.dto import PersonaDTO
    from app.ui.vistas.main_window.state_controller import MainWindow


logger = logging.getLogger(__name__)


def is_form_dirty(window: MainWindow) -> bool:
    return bool(window.notas_input.toPlainText().strip()) or window.fecha_input.date() != QDate.currentDate() or window.desde_input.time() != QTime(9, 0) or window.hasta_input.time() != QTime(17, 0) or window.completo_check.isChecked()


def confirmar_cambio_delegada(window: MainWindow) -> bool:
    respuesta = QMessageBox.question(
        window,
        copy_text("ui.personas.cambiar_delegada_titulo"),
        copy_text("ui.personas.cambiar_delegada_mensaje"),
    )
    return respuesta == QMessageBox.StandardButton.Yes


def save_current_draft(window: MainWindow, persona_id: int | None) -> None:
    if persona_id is None:
        return
    if not is_form_dirty(window):
        window._draft_solicitud_por_persona.pop(persona_id, None)
        return
    window._draft_solicitud_por_persona[persona_id] = {
        "fecha": window.fecha_input.date(),
        "desde": window.desde_input.time(),
        "hasta": window.hasta_input.time(),
        "completo": window.completo_check.isChecked(),
        "notas": window.notas_input.toPlainText(),
    }


def restore_draft_for_persona(window: MainWindow, persona_id: int | None) -> None:
    if persona_id is None:
        return
    draft = window._draft_solicitud_por_persona.get(persona_id)
    if not draft:
        return
    window.fecha_input.setDate(draft["fecha"])
    window.desde_input.setTime(draft["desde"])
    window.hasta_input.setTime(draft["hasta"])
    window.completo_check.setChecked(bool(draft["completo"]))
    window.notas_input.setPlainText(str(draft["notas"]))


def _reload_historico_delegada_combo(window: MainWindow, items: tuple[tuple[str, int | None], ...]) -> None:
    window.historico_delegada_combo.blockSignals(True)
    window.historico_delegada_combo.clear()
    for nombre, persona_id in items:
        window.historico_delegada_combo.addItem(nombre, persona_id)
    window.historico_delegada_combo.blockSignals(False)


def _reload_config_delegada_combo(window: MainWindow, items: tuple[tuple[str, int], ...], active_id: int | None) -> None:
    window.config_delegada_combo.blockSignals(True)
    window.config_delegada_combo.clear()
    for nombre, persona_id in items:
        # Nunca usar el texto visible para identificar registros: puede repetirse.
        # Usamos siempre persona_id (delegada_id real) en userData.
        window.config_delegada_combo.addItem(nombre, persona_id)
    if active_id is not None:
        for index in range(window.config_delegada_combo.count()):
            if window.config_delegada_combo.itemData(index) == active_id:
                window.config_delegada_combo.setCurrentIndex(index)
                break
    window.config_delegada_combo.blockSignals(False)


def load_personas(window: MainWindow, select_id: int | None = None) -> None:
    window._personas = list(window._persona_use_cases.listar())
    presenter_output = build_personas_load_output(
        PersonasLoadInput(
            personas=tuple(PersonaOption(id=persona.id, nombre=persona.nombre) for persona in window._personas),
            select_id=select_id,
            saved_delegada_id=window._settings.value(CLAVE_CONTEXTO_DELEGADA_SELECCIONADA_ID, None),
        )
    )

    window.persona_combo.blockSignals(True)
    window.persona_combo.clear()
    for persona in presenter_output.persona_items:
        window.persona_combo.addItem(persona.nombre, persona.id)
    if presenter_output.selected_persona_id is not None:
        for index in range(window.persona_combo.count()):
            if window.persona_combo.itemData(index) == presenter_output.selected_persona_id:
                window.persona_combo.setCurrentIndex(index)
                break
    window.persona_combo.blockSignals(False)

    window._last_persona_id = window.persona_combo.currentData()
    persona_nombres = presenter_output.persona_nombres
    window.pendientes_model.set_persona_nombres(persona_nombres)
    window.huerfanas_model.set_persona_nombres(persona_nombres)
    window.historico_model.set_persona_nombres(persona_nombres)

    _reload_historico_delegada_combo(window, presenter_output.historico_items)
    _reload_config_delegada_combo(window, presenter_output.config_items, presenter_output.active_config_id)
    sync_config_persona_actions(window)
    on_persona_changed(window)


def current_persona(window: MainWindow) -> PersonaDTO | None:
    index = window.persona_combo.currentIndex()
    if index < 0:
        return None
    persona_id = window.persona_combo.currentData()
    for persona in window._personas:
        if persona.id == persona_id:
            return persona
    return None


def on_persona_changed(window: MainWindow, *_args) -> None:
    nueva_persona_id = window.persona_combo.currentData()

    if window._last_persona_id != nueva_persona_id and is_form_dirty(window) and not confirmar_cambio_delegada(window):
        for index in range(window.persona_combo.count()):
            if window.persona_combo.itemData(index) == window._last_persona_id:
                window.persona_combo.setCurrentIndex(index)
                break
        return

    if window._last_persona_id != nueva_persona_id:
        save_current_draft(window, window._last_persona_id)
        window._limpiar_formulario()
        restore_draft_for_persona(window, nueva_persona_id)

    window._last_persona_id = nueva_persona_id
    window.pendientes_table.clearSelection()
    window.huerfanas_table.clearSelection()
    window._reload_pending_views()
    window._update_action_state()
    window._refresh_saldos()
    window._update_solicitud_preview()
    window._update_global_context()


def on_add_persona(window: MainWindow) -> None:
    dialog = PersonaDialog(window)
    persona_dto = dialog.get_persona()
    if persona_dto is None:
        logger.info("Creación de persona cancelada")
        return
    window._personas_controller.on_add_persona(persona_dto)


def selected_config_persona(window: MainWindow) -> PersonaDTO | None:
    persona_id = window.config_delegada_combo.currentData()
    if persona_id is None:
        return None
    for persona in window._personas:
        if persona.id == persona_id:
            return persona
    return None


def on_edit_persona(window: MainWindow) -> None:
    persona = selected_config_persona(window)
    if persona is None:
        window.toast.warning(
            copy_text("ui.personas.selecciona_delegada_editar"),
            title=copy_text("ui.personas.delegada_requerida"),
        )
        return
    dialog = PersonaDialog(window, persona)
    persona_dto = dialog.get_persona()
    if persona_dto is None:
        logger.info("Edición de persona cancelada")
        return
    confirm = QMessageBox.question(
        window,
        copy_text("ui.personas.confirmar_cambios_titulo"),
        copy_text("ui.personas.confirmar_cambios_mensaje"),
    )
    if confirm != QMessageBox.StandardButton.Yes:
        return
    try:
        actualizada = window._persona_use_cases.editar_persona(persona_dto)
    except (ValidacionError, BusinessRuleError) as exc:
        window.toast.warning(str(exc), title=copy_text("ui.validacion.validacion"))
        return
    except Exception as exc:  # pragma: no cover - fallback
        logger.exception("Error editando persona")
        window._show_critical_error(exc)
        return
    load_personas(window, select_id=actualizada.id)


def on_delete_persona(window: MainWindow) -> None:
    persona = selected_config_persona(window)
    if persona is None:
        window.toast.warning(
            copy_text("ui.personas.selecciona_delegada_eliminar"),
            title=copy_text("ui.personas.delegada_requerida"),
        )
        return
    logger.info("Se pide confirmación de borrado motivo=policy=always_confirm selection_count=1")
    respuesta = QMessageBox.question(
        window,
        copy_text("ui.personas.eliminar_delegada_titulo"),
        copy_text("ui.personas.eliminar_delegada_mensaje").format(nombre=persona.nombre),
    )
    if respuesta != QMessageBox.StandardButton.Yes:
        return
    try:
        window._persona_use_cases.desactivar_persona(persona.id or 0)
    except (ValidacionError, BusinessRuleError) as exc:
        window.toast.warning(str(exc), title=copy_text("ui.validacion.validacion"))
        return
    except Exception as exc:  # pragma: no cover - fallback
        logger.exception("Error deshabilitando delegado")
        window._show_critical_error(exc)
        return
    load_personas(window)


def sync_config_persona_actions(window: MainWindow) -> None:
    has_selected_persona = window.config_delegada_combo.currentData() is not None
    window.edit_persona_button.setEnabled(has_selected_persona)
    window.delete_persona_button.setEnabled(has_selected_persona)


def on_config_delegada_changed(window: MainWindow, *_args) -> None:
    persona_id = window.config_delegada_combo.currentData()
    sync_config_persona_actions(window)
    window._settings.setValue(CLAVE_CONTEXTO_DELEGADA_ACTIVA, persona_id)
    window._settings.setValue(CLAVE_CONTEXTO_DELEGADA_SELECCIONADA_ID, persona_id)
    if persona_id is None:
        return
    for index in range(window.persona_combo.count()):
        if window.persona_combo.itemData(index) == persona_id:
            window.persona_combo.setCurrentIndex(index)
            break


def restaurar_contexto_guardado(window: MainWindow) -> None:
    delegada_id = window._settings.value(CLAVE_CONTEXTO_DELEGADA_SELECCIONADA_ID, None)
    historico_id = window._settings.value(CLAVE_HISTORICO_DELEGADA, None)
    for combo, value in ((window.config_delegada_combo, delegada_id), (window.historico_delegada_combo, historico_id)):
        for index in range(combo.count()):
            if str(combo.itemData(index)) == str(value):
                combo.setCurrentIndex(index)
                break


def configure_operativa_focus_order(window: MainWindow) -> None:
    window.setTabOrder(window.persona_combo, window.fecha_input)
    window.setTabOrder(window.fecha_input, window.desde_input)
    window.setTabOrder(window.desde_input, window.hasta_input)
    window.setTabOrder(window.hasta_input, window.completo_check)
    window.setTabOrder(window.completo_check, window.notas_input)
    window.setTabOrder(window.notas_input, window.agregar_button)
    window.setTabOrder(window.agregar_button, window.insertar_sin_pdf_button)
    window.setTabOrder(window.insertar_sin_pdf_button, window.confirmar_button)


def update_responsive_columns(window: MainWindow) -> None:
    if not hasattr(window, "solicitudes_splitter"):
        return
    available_width = window._scroll_area.viewport().width() if hasattr(window, "_scroll_area") else window.width()
    left_size = max(300, int(available_width * 0.4))
    right_size = max(420, int(available_width * 0.6))
    window.solicitudes_splitter.setSizes([left_size, right_size])


def normalize_input_heights(window: MainWindow) -> None:
    controls = [
        window.persona_combo,
        window.fecha_input,
        window.desde_input,
        window.hasta_input,
        window.historico_search_input,
        window.historico_estado_combo,
        window.historico_delegada_combo,
        window.historico_desde_date,
        window.historico_hasta_date,
        window.open_saldos_modal_button,
        window.add_persona_button,
        window.edit_persona_button,
        window.edit_grupo_button,
        window.opciones_button,
        window.delete_persona_button,
        window.agregar_button,
        window.eliminar_pendiente_button,
        window.editar_pdf_button,
        window.insertar_sin_pdf_button,
        window.confirmar_button,
        window.eliminar_button,
        window.generar_pdf_button,
    ]
    for control in controls:
        control.setMinimumHeight(40)


def on_open_saldos_modal(window: object) -> None:
    """Abre el modal de saldos de forma segura."""

    dialogo_class = getattr(window, "_saldos_dialog_class", None)
    if dialogo_class is None:
        mensaje = copy_text("ui.saldos.modal_no_disponible")
        titulo = copy_text("ui.saldos.modal_no_disponible_titulo")
        if hasattr(window, "toast") and hasattr(window.toast, "warning"):
            window.toast.warning(mensaje, title=titulo)
            return
        if hasattr(QMessageBox, "information"):
            QMessageBox.information(window, titulo, mensaje)
        return

    dialogo = dialogo_class(window)
    window._dialogo_saldos = dialogo
    ejecutar_modal = getattr(dialogo, "exec", None)
    if callable(ejecutar_modal):
        ejecutar_modal()
        return

    mostrar_dialogo = getattr(dialogo, "show", None)
    if callable(mostrar_dialogo):
        mostrar_dialogo()
