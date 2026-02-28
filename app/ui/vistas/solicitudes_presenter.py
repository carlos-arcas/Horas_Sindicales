from __future__ import annotations

from dataclasses import dataclass

from app.application.dto import SolicitudDTO
from app.application.use_cases.solicitudes.validaciones import (
    clave_duplicado_solicitud,
)


@dataclass(frozen=True)
class PreventiveValidationViewInput:
    blocking_errors: dict[str, str]
    field_touched: set[str]
    has_duplicate_target: bool


@dataclass(frozen=True)
class PreventiveValidationViewOutput:
    delegada_error: str
    fecha_error: str
    tramo_error: str
    summary_items: tuple[str, ...]
    summary_text: str
    show_pending_errors_frame: bool
    show_duplicate_cta: bool


@dataclass(frozen=True)
class ActionStateInput:
    persona_selected: bool
    form_valid: bool
    has_blocking_errors: bool
    is_editing_pending: bool
    has_pending: bool
    has_pending_conflicts: bool
    pendientes_count: int
    selected_historico_count: int


@dataclass(frozen=True)
class ActionStateOutput:
    agregar_enabled: bool
    agregar_text: str
    insertar_sin_pdf_enabled: bool
    pendientes_count: int
    edit_persona_enabled: bool
    delete_persona_enabled: bool
    edit_grupo_enabled: bool
    editar_pdf_enabled: bool
    eliminar_enabled: bool
    eliminar_text: str
    generar_pdf_enabled: bool
    generar_pdf_text: str
    eliminar_pendiente_enabled: bool


@dataclass(frozen=True)
class DuplicateSearchInput:
    solicitud: SolicitudDTO
    pending_solicitudes: list[SolicitudDTO]
    editing_pending_id: int | None
    editing_row: int | None
    duplicated_keys: set[tuple[str, ...]]


def build_preventive_validation_view_model(
    data: PreventiveValidationViewInput,
) -> PreventiveValidationViewOutput:
    delegada_error = data.blocking_errors.get("delegada", "") if "delegada" in data.field_touched else ""
    fecha_error = data.blocking_errors.get("fecha", "") if "fecha" in data.field_touched else ""
    tramo_error = data.blocking_errors.get("tramo", "") if "tramo" in data.field_touched else ""

    summary_items = tuple(
        message
        for key, message in data.blocking_errors.items()
        if key not in {"delegada", "fecha", "tramo"} or key in data.field_touched
    )
    if not summary_items:
        summary_items = tuple(data.blocking_errors.values())
    summary_text = "\n".join(f"• {message}" for message in summary_items)

    show_duplicate_cta = "duplicado" in data.blocking_errors and data.has_duplicate_target
    return PreventiveValidationViewOutput(
        delegada_error=delegada_error,
        fecha_error=fecha_error,
        tramo_error=tramo_error,
        summary_items=summary_items,
        summary_text=summary_text,
        show_pending_errors_frame=bool(summary_items),
        show_duplicate_cta=show_duplicate_cta,
    )


def build_action_state(data: ActionStateInput) -> ActionStateOutput:
    can_add_or_update = data.persona_selected and data.form_valid and not data.has_blocking_errors
    can_confirm_without_pdf = data.has_pending and not data.has_pending_conflicts and not data.has_blocking_errors
    has_selected_historico = data.selected_historico_count > 0

    return ActionStateOutput(
        agregar_enabled=can_add_or_update,
        agregar_text="Actualizar pendiente" if data.is_editing_pending else "Añadir pendiente",
        insertar_sin_pdf_enabled=data.persona_selected and can_confirm_without_pdf,
        pendientes_count=data.pendientes_count,
        edit_persona_enabled=data.persona_selected,
        delete_persona_enabled=data.persona_selected,
        edit_grupo_enabled=True,
        editar_pdf_enabled=True,
        eliminar_enabled=data.persona_selected and has_selected_historico,
        eliminar_text=f"Eliminar ({data.selected_historico_count})",
        generar_pdf_enabled=data.persona_selected and has_selected_historico,
        generar_pdf_text=f"Exportar histórico PDF ({data.selected_historico_count})",
        eliminar_pendiente_enabled=data.has_pending,
    )


def find_pending_duplicate_row(data: DuplicateSearchInput) -> int | None:
    try:
        target_key = clave_duplicado_solicitud(data.solicitud)
    except Exception:
        return None

    matches: list[int] = []
    for row, pending in enumerate(data.pending_solicitudes):
        if data.editing_pending_id is not None and pending.id is not None and str(pending.id) == str(data.editing_pending_id):
            continue
        if pending.id is None and data.editing_row is not None and row == data.editing_row:
            continue
        try:
            if clave_duplicado_solicitud(pending) == target_key:
                matches.append(row)
        except Exception:
            continue

    duplicate_key = tuple(list(target_key) + ["COMPLETO" if data.solicitud.completo else "PARCIAL"])
    if duplicate_key not in data.duplicated_keys:
        return None
    if matches:
        return matches[0]
    if data.pending_solicitudes:
        return 0
    return None
