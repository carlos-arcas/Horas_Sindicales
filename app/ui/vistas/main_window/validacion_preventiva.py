from __future__ import annotations

import logging
from datetime import datetime

from app.application.dto import SolicitudDTO
from app.application.use_cases.solicitudes.validaciones import detectar_duplicados_en_pendientes
from app.bootstrap.logging import log_operational_error
from app.domain.request_time import validate_request_inputs
from app.domain.services import BusinessRuleError, ValidacionError
from app.ui.copy_catalog import copy_text
from app.ui.vistas.solicitudes_presenter import PreventiveValidationViewInput, build_preventive_validation_view_model
from app.ui.vistas.solicitudes_ux_rules import (
    SolicitudesFocusInput,
    SolicitudesStatusInput,
    build_solicitudes_status,
    resolve_first_invalid_field,
)

logger = logging.getLogger(__name__)


def es_fecha_iso_valida(fecha_texto: str) -> bool:
    try:
        datetime.strptime(fecha_texto, "%Y-%m-%d")
    except ValueError:
        return False
    return True


def validar_tramo_preventivo(desde: str | None, hasta: str | None, completo: bool) -> str | None:
    tramo_errors = validate_request_inputs(desde, hasta, completo)
    if not tramo_errors:
        return None
    return next(iter(tramo_errors.values()))


def _bind_preventive_validation_events(window) -> None:
    window.persona_combo.currentIndexChanged.connect(lambda _: _mark_field_touched(window, "delegada"))
    window.fecha_input.editingFinished.connect(lambda: _mark_field_touched(window, "fecha"))
    window.desde_input.editingFinished.connect(lambda: _mark_field_touched(window, "tramo"))
    window.hasta_input.editingFinished.connect(lambda: _mark_field_touched(window, "tramo"))
    window.completo_check.toggled.connect(lambda _: _mark_field_touched(window, "tramo"))


def _mark_field_touched(window, field: str) -> None:
    window._field_touched.add(field)
    _schedule_preventive_validation(window)


def _schedule_preventive_validation(window) -> None:
    if window._preventive_validation_in_progress:
        return
    window._preventive_validation_timer.start(window._preventive_validation_debounce_ms)


def _run_preventive_validation(window) -> None:
    if window._preventive_validation_in_progress:
        return
    window._preventive_validation_in_progress = True
    try:
        blocking, warnings = _collect_preventive_validation(window)
        window._blocking_errors = blocking
        window._warnings = warnings
        _render_preventive_validation(window)
        window._dump_estado_pendientes("after_run_preventive_validation")
    finally:
        window._preventive_validation_in_progress = False


def _collect_base_preventive_errors(window) -> dict[str, str]:
    blocking: dict[str, str] = {}
    if window._current_persona() is None:
        blocking["delegada"] = copy_text("solicitudes.validation_delegada")

    fecha_pedida = window.fecha_input.date().toString("yyyy-MM-dd")
    if not es_fecha_iso_valida(fecha_pedida):
        blocking["fecha"] = copy_text("solicitudes.validation_fecha")

    completo = window.completo_check.isChecked()
    detalle_tramo = validar_tramo_preventivo(
        None if completo else window.desde_input.time().toString("HH:mm"),
        None if completo else window.hasta_input.time().toString("HH:mm"),
        completo,
    )
    if detalle_tramo is not None:
        blocking["tramo"] = f"{copy_text('solicitudes.validation_tramo_prefix')} {detalle_tramo}"
    return blocking


def _collect_preventive_business_rules(
    window,
    solicitud: SolicitudDTO,
    warnings: dict[str, str],
    blocking: dict[str, str],
) -> None:
    minutos = window._solicitud_use_cases.calcular_minutos_solicitud(solicitud)
    year, month, _ = (int(part) for part in solicitud.fecha_pedida.split("-"))
    saldos = window._solicitud_use_cases.calcular_saldos(solicitud.persona_id, year, month)
    if saldos.restantes_mes < minutos or saldos.restantes_ano < minutos:
        warnings["saldo"] = "Saldo insuficiente. La petición se ha registrado igualmente."

    similares = list(window._solicitud_use_cases.buscar_similares(solicitud))
    if similares:
        ids_similares = [str(item.id) for item in similares if item.id is not None]
        warnings["similares"] = "Posibles similares: " + ", ".join(ids_similares)

    conflicto = window._solicitud_use_cases.validar_conflicto_dia(
        solicitud.persona_id, solicitud.fecha_pedida, solicitud.completo
    )
    if not conflicto.ok:
        blocking["conflicto"] = copy_text("solicitudes.validation_conflict")

    if solicitud.completo and window.cuadrante_warning_label.isVisible():
        warnings["cuadrante"] = "⚠ El cuadrante no está configurado y puede alterar el cálculo final."


def _collect_pending_duplicates_warning(window, warnings: dict[str, str]) -> None:
    claves_duplicadas = detectar_duplicados_en_pendientes(window._pending_solicitudes)
    if not claves_duplicadas:
        return
    warnings["duplicados_pendientes"] = "Hay duplicados en pendientes."
    window._duplicate_target = window._pending_solicitudes[0] if window._pending_solicitudes else None


def _build_preview_solicitud(window) -> SolicitudDTO | None:
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


def _collect_preventive_validation(window) -> tuple[dict[str, str], dict[str, str]]:
    blocking = _collect_base_preventive_errors(window)
    warnings: dict[str, str] = {}
    window._duplicate_target = None
    _collect_pending_duplicates_warning(window, warnings)

    solicitud = window._build_preview_solicitud()
    if solicitud is None or blocking:
        return blocking, warnings

    try:
        db_locked_error = window._validacion_preventiva_lock_use_case.ejecutar(
            lambda: _collect_preventive_business_rules(window, solicitud, warnings, blocking)
        )
        if db_locked_error is not None:
            log_operational_error(
                logger,
                "DB locked during preventive validation",
                exc=db_locked_error,
                extra={
                    "operation": "preventive_validation",
                    "persona_id": solicitud.persona_id,
                },
            )
            warnings["db"] = "Validación parcial temporal: base de datos ocupada. Vuelve a intentar en unos segundos."
    except (ValidacionError, BusinessRuleError) as exc:
        blocking.setdefault("tramo", f"{copy_text('solicitudes.validation_tramo_prefix')} {str(exc)}")

    window._dump_estado_pendientes("after_collect_preventive_validation")
    return blocking, warnings


def _render_preventive_validation(window) -> None:
    if not window._ui_ready:
        return
    view_model = build_preventive_validation_view_model(
        PreventiveValidationViewInput(
            blocking_errors=window._blocking_errors,
            field_touched=window._field_touched,
            has_duplicate_target=window._duplicate_target is not None,
        )
    )
    window.delegada_field_error.setVisible(bool(view_model.delegada_error))
    window.delegada_field_error.setText(view_model.delegada_error)
    window.fecha_field_error.setVisible(bool(view_model.fecha_error))
    window.fecha_field_error.setText(view_model.fecha_error)
    window.tramo_field_error.setVisible(bool(view_model.tramo_error))
    window.tramo_field_error.setText(view_model.tramo_error)
    window.pending_errors_frame.setVisible(view_model.show_pending_errors_frame)
    summary_text = view_model.summary_text
    if summary_text:
        summary_text = f"{copy_text('solicitudes.pending_errors_intro')}\n{summary_text}"
    window.pending_errors_summary.setText(summary_text)
    show_duplicate_cta = view_model.show_duplicate_cta
    window.goto_existing_button.setVisible(show_duplicate_cta)
    logger.debug(
        "duplicate_banner_updated visible=%s has_duplicate_error=%s duplicate_target_id=%s",
        show_duplicate_cta,
        "duplicado" in window._blocking_errors,
        window._duplicate_target.id if window._duplicate_target is not None else None,
    )


def _on_go_to_existing_duplicate(window) -> None:
    duplicate = window._duplicate_target
    if duplicate is None:
        return
    if not duplicate.generated:
        if window._focus_pending_by_id(duplicate.id):
            return
        duplicate_row = window._find_pending_duplicate_row(duplicate)
        if duplicate_row is not None:
            window._focus_pending_row(duplicate_row)
            return
    window._focus_historico_duplicate(duplicate)


def _run_preconfirm_checks(window) -> bool:
    window._field_touched.update({"delegada", "fecha", "tramo"})
    _run_preventive_validation(window)
    if window._blocking_errors:
        window._focus_first_invalid_field()
        window.toast.warning(copy_text("solicitudes.validation_blocking_toast"), title="Validación preventiva")
        return False
    if window._warnings:
        warning_text = "\n".join(f"• {msg}" for msg in window._warnings.values())
        window.toast.info(
            f"Se detectaron advertencias no bloqueantes:\n{warning_text}",
            title="Advertencias",
        )
    return True


def _calculate_preview_minutes(window) -> tuple[int | None, bool]:
    solicitud = window._build_preview_solicitud()
    if solicitud is None:
        return None, False
    try:
        minutos = window._solicitud_use_cases.calcular_minutos_solicitud(solicitud)
        return minutos, False
    except BusinessRuleError as exc:
        mensaje = str(exc).lower()
        warning = solicitud.completo and "configura el cuadrante" in mensaje
        return None, warning


def _update_solicitud_preview(window) -> None:
    if not window._ui_ready:
        return
    valid, _message = window._validate_solicitud_form()
    minutos, warning = window._calculate_preview_minutes()
    total_txt = "—" if minutos is None or not valid else window._format_minutes(minutos)
    window.total_preview_input.setText(total_txt)
    window.cuadrante_warning_label.setVisible(warning)
    window.cuadrante_warning_label.setText("Cuadrante no configurado" if warning else "")
    window.solicitud_inline_error.setVisible(False)
    window.solicitud_inline_error.setText("")
    window._solicitudes_last_action_saved = False
    _run_preventive_validation(window)
    window._update_action_state()


def _validate_solicitud_form(window) -> tuple[bool, str]:
    if window._current_persona() is None:
        return False, "Selecciona una persona para crear la solicitud."
    completo = window.completo_check.isChecked()
    detalle_tramo = validar_tramo_preventivo(
        None if completo else window.desde_input.time().toString("HH:mm"),
        None if completo else window.hasta_input.time().toString("HH:mm"),
        completo,
    )
    if detalle_tramo is not None:
        return False, detalle_tramo
    return True, ""


def _focus_first_invalid_field(window) -> None:
    first_field = resolve_first_invalid_field(SolicitudesFocusInput(blocking_errors=window._blocking_errors))
    mapping = {"delegada": window.persona_combo, "fecha": window.fecha_input, "tramo": window.desde_input}
    target = mapping.get(first_field)
    if target is not None:
        target.setFocus()


def _manual_hours_minutes(window) -> int:
    horas_input = getattr(window, "horas_input", None)
    if horas_input is None:
        return 0
    if hasattr(horas_input, "minutes"):
        return max(0, int(horas_input.minutes()))
    if hasattr(horas_input, "time"):
        qtime = horas_input.time()
        return (qtime.hour() * 60) + qtime.minute()
    if hasattr(horas_input, "value"):
        return max(0, int(horas_input.value() * 60))
    return 0


def _bind_manual_hours_preview_refresh(window) -> None:
    if not hasattr(window, "horas_input"):
        return
    horas_input = window.horas_input
    for signal_name in ("minutesChanged", "timeChanged", "valueChanged", "textChanged"):
        signal = getattr(horas_input, signal_name, None)
        if signal is None:
            continue
        try:
            signal.connect(window._update_solicitud_preview)
        except Exception:  # pragma: no cover - compatibilidad entre widgets Qt
            continue


def _update_solicitudes_status_panel(window) -> None:
    if window.solicitudes_status_label is None or window.solicitudes_status_hint is None:
        return
    persona = window._current_persona()
    nombre_delegada = getattr(persona, "nombre", None) if persona is not None else None
    seleccionadas = len(window._selected_pending_solicitudes()) if hasattr(window, "_selected_pending_solicitudes") else 0
    saldo_reservado = window.total_pendientes_label.text().split(":", 1)[-1].strip() if getattr(window, "total_pendientes_label", None) is not None else "00:00"
    status = build_solicitudes_status(
        SolicitudesStatusInput(
            delegada_actual=nombre_delegada,
            pendientes_visibles=len(window._pending_solicitudes),
            pendientes_seleccionadas=seleccionadas,
            saldo_reservado=saldo_reservado,
            has_blocking_errors=bool(getattr(window, "_blocking_errors", {})),
            has_runtime_error=window._solicitudes_runtime_error,
            hay_conflictos_pendientes=bool(getattr(window, "_pending_conflict_rows", set())),
            puede_confirmar_pdf=bool(getattr(window, "confirmar_button", None) and window.confirmar_button.isEnabled()),
        )
    )
    seleccion_texto = copy_text(status.label_params["seleccion_key"])
    label_params = dict(status.label_params)
    label_params["seleccion"] = seleccion_texto
    window.solicitudes_status_label.setText(copy_text(status.label_key).format(**label_params))
    window.solicitudes_status_hint.setText(copy_text(status.action_key))

    window._solicitudes_help_key_actual = status.help_key
    ayuda_disponible = status.help_key is not None
    if hasattr(window, "show_help_toggle") and window.show_help_toggle is not None:
        window.show_help_toggle.setEnabled(ayuda_disponible)
        window.show_help_toggle.setVisible(ayuda_disponible)
    if not ayuda_disponible:
        window.solicitudes_tip_1.setVisible(False)
        window.solicitudes_tip_2.setVisible(False)
        window.solicitudes_tip_3.setVisible(False)
        return

    ayuda_texto = copy_text(status.help_key)
    window.solicitudes_tip_1.setText(ayuda_texto)
    window.solicitudes_tip_2.setVisible(False)
    window.solicitudes_tip_3.setVisible(False)
