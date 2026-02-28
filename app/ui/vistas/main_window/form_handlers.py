from __future__ import annotations

import logging
from datetime import datetime

try:
    from PySide6.QtCore import QDate, QTime
    from PySide6.QtWidgets import QCheckBox, QComboBox, QDateEdit, QLabel, QPlainTextEdit, QTimeEdit
except Exception:  # pragma: no cover
    QDate = QTime = object
    QCheckBox = QComboBox = QDateEdit = QLabel = QPlainTextEdit = QTimeEdit = object

from app.application.dto import SolicitudDTO

logger = logging.getLogger(__name__)


def limpiar_formulario(window) -> None:
    window.fecha_input.setDate(QDate.currentDate())
    window.desde_input.setTime(QTime(9, 0))
    window.hasta_input.setTime(QTime(17, 0))
    window.completo_check.setChecked(False)
    window.notas_input.clear()
    window._field_touched.clear()
    window._blocking_errors.clear()
    window._warnings.clear()
    window.solicitud_inline_error.setVisible(False)
    window.delegada_field_error.setVisible(False)
    window.fecha_field_error.setVisible(False)
    window.tramo_field_error.setVisible(False)
    window._update_solicitud_preview()
    window._update_action_state()
    logger.info("formulario_limpiado")


def clear_form(window) -> None:
    limpiar_formulario_method = getattr(window, "_limpiar_formulario", None)
    if callable(limpiar_formulario_method):
        try:
            limpiar_formulario_method()
        except AttributeError:
            pass

    persona_combo = getattr(window, "persona_combo", None)
    if isinstance(persona_combo, QComboBox):
        persona_combo.setCurrentIndex(-1)

    fecha_input = getattr(window, "fecha_input", None)
    if isinstance(fecha_input, QDateEdit):
        fecha_input.setDate(QDate.currentDate())

    desde_input = getattr(window, "desde_input", None)
    if isinstance(desde_input, QTimeEdit):
        desde_input.setTime(QTime(9, 0))

    hasta_input = getattr(window, "hasta_input", None)
    if isinstance(hasta_input, QTimeEdit):
        hasta_input.setTime(QTime(17, 0))

    completo_check = getattr(window, "completo_check", None)
    if isinstance(completo_check, QCheckBox):
        completo_check.setChecked(False)

    notas_input = getattr(window, "notas_input", None)
    if isinstance(notas_input, QPlainTextEdit):
        notas_input.clear()

    for attr_name in ("_field_touched", "_blocking_errors", "_warnings"):
        state = getattr(window, attr_name, None)
        if hasattr(state, "clear"):
            state.clear()

    for label_name in (
        "solicitud_inline_error",
        "delegada_field_error",
        "fecha_field_error",
        "tramo_field_error",
    ):
        label = getattr(window, label_name, None)
        if isinstance(label, QLabel):
            label.setVisible(False)

    update_preview = getattr(window, "_update_solicitud_preview", None)
    if callable(update_preview):
        update_preview()

    update_actions = getattr(window, "_update_action_state", None)
    if callable(update_actions):
        update_actions()


def build_preview_solicitud(window) -> SolicitudDTO | None:
    persona = window._current_persona()
    if persona is None:
        return None
    completo = window.completo_check.isChecked()
    fecha_pedida = window.fecha_input.date().toString("yyyy-MM-dd")
    desde = None if completo else window.desde_input.time().toString("HH:mm")
    hasta = None if completo else window.hasta_input.time().toString("HH:mm")
    manual_minutes = window._manual_hours_minutes()
    editing_pending = window._selected_pending_for_editing()
    return SolicitudDTO(
        id=editing_pending.id if editing_pending is not None else None,
        persona_id=persona.id or 0,
        fecha_solicitud=datetime.now().strftime("%Y-%m-%d"),
        fecha_pedida=fecha_pedida,
        desde=desde,
        hasta=hasta,
        completo=completo,
        horas=manual_minutes / 60 if manual_minutes > 0 else 0,
        observaciones=None,
        pdf_path=None,
        pdf_hash=None,
        notas=None,
    )
