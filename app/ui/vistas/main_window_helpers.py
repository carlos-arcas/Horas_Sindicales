from __future__ import annotations

import json
import logging
from typing import Callable

from PySide6.QtWidgets import QMessageBox

from app.application.dto import SolicitudDTO
from app.application.use_cases.solicitudes.validaciones import (
    clave_duplicado_solicitud,
    detectar_duplicados_en_pendientes,
)
from app.ui.error_mapping import map_error_to_ui_message
from app.domain.sheets_errors import (
    SheetsApiDisabledError,
    SheetsConfigError,
    SheetsCredentialsError,
    SheetsNotFoundError,
    SheetsPermissionError,
    SheetsRateLimitError,
)

logger = logging.getLogger(__name__)


def build_estado_pendientes_debug_payload(
    *,
    editing_pending: SolicitudDTO | None,
    selected_rows: list[int],
    solicitud_form: SolicitudDTO | None,
    pending_solicitudes: list[SolicitudDTO],
    agregar_button_text: str,
    agregar_button_enabled: bool,
) -> dict[str, object]:
    """Extraído para reducir LOC de la vista y facilitar tests de diagnóstico."""
    dto_form_actual = None
    clave_form_normalizada = None
    duplicate_eval: dict[str, object] = {
        "function": "detectar_duplicados_en_pendientes",
        "params": {
            "pendientes_count": len(pending_solicitudes),
        },
        "resultado": None,
    }
    if solicitud_form is not None:
        dto_form_actual = {
            "persona_id": solicitud_form.persona_id,
            "fecha": solicitud_form.fecha_pedida,
            "desde": solicitud_form.desde,
            "hasta": solicitud_form.hasta,
            "completo": solicitud_form.completo,
        }
        clave_form_normalizada = list(clave_duplicado_solicitud(solicitud_form))
        duplicate_eval["resultado"] = [
            list(clave)
            for clave in detectar_duplicados_en_pendientes(pending_solicitudes)
        ]

    lista_pendientes = []
    for index, pendiente in enumerate(pending_solicitudes):
        lista_pendientes.append(
            {
                "id": pendiente.id,
                "index": index,
                "clave_normalizada": list(clave_duplicado_solicitud(pendiente)),
            }
        )

    return {
        "editing_pending_id": editing_pending.id if editing_pending is not None else None,
        "editing_pending_index": selected_rows[0] if editing_pending is not None and selected_rows else None,
        "selected_pending_rows": selected_rows,
        "selected_pending_count": len(selected_rows),
        "dto_form_actual": dto_form_actual,
        "clave_form_normalizada": clave_form_normalizada,
        "lista_pendientes": lista_pendientes,
        "duplicados_en_pendientes": duplicate_eval,
        "cta_decision": {
            "text": agregar_button_text,
            "enabled": bool(agregar_button_enabled),
            "reason": "form_add_or_update",
            "hint": "",
        },
    }


def show_sync_error_dialog_from_exception(
    *,
    error: Exception,
    details: str | None,
    service_account_email: str | None,
    show_message_with_details: Callable[..., None],
    open_options_callback: Callable[[], None],
    retry_callback: Callable[[], None],
    open_google_sheets_config_callback: Callable[[], None] | None = None,
    toast_warning: Callable[[str, str, int], None],
) -> None:
    """Extraído para desacoplar mapeo de errores y permitir testear rutas sin la MainWindow."""
    if details:
        logger.error("Detalle técnico de sincronización: %s", details)
    title = "Error de sincronización"
    icon = QMessageBox.Critical

    if isinstance(error, SheetsApiDisabledError):
        show_message_with_details(
            title,
            "No se pudo sincronizar.\n"
            "Causa probable: La API de Google Sheets no está habilitada en el proyecto de Google Cloud.\n"
            "Acción recomendada: Actívala en Google Cloud Console y vuelve a reintentar en 2-5 minutos.",
            None,
            icon,
            action_buttons=(("Ir a configuración", open_options_callback), ("Reintentar", retry_callback)),
        )
        return
    if isinstance(error, SheetsPermissionError):
        email_hint = f"{service_account_email}" if service_account_email else "la cuenta de servicio"
        show_message_with_details(
            title,
            "No se pudo sincronizar.\n"
            f"Causa probable: La hoja no está compartida con {email_hint}.\n"
            f"Acción recomendada: Comparte el spreadsheet con la cuenta de servicio: {email_hint}.",
            None,
            icon,
            action_buttons=(("Abrir configuración de Google Sheets", open_google_sheets_config_callback or open_options_callback), ("Reintentar", retry_callback)),
        )
        return
    if isinstance(error, SheetsNotFoundError):
        show_message_with_details(
            title,
            "No se pudo sincronizar.\n"
            "Causa probable: El Spreadsheet ID/URL es inválido o la hoja no existe.\n"
            "Acción recomendada: Revisa el ID/URL en configuración y vuelve a intentarlo.",
            None,
            icon,
            action_buttons=(("Ir a configuración", open_options_callback),),
        )
        return
    if isinstance(error, SheetsCredentialsError):
        show_message_with_details(
            title,
            "No se pudo sincronizar.\n"
            "Causa probable: La credencial JSON no es válida o no se puede leer.\n"
            "Acción recomendada: Selecciona de nuevo el archivo de credenciales en configuración.",
            None,
            icon,
            action_buttons=(("Ir a configuración", open_options_callback),),
        )
        return
    if isinstance(error, SheetsRateLimitError):
        toast_warning(
            "Límite de Google Sheets alcanzado. Espera 1 minuto y reintenta.",
            "Sincronización pausada",
            6000,
        )
        show_message_with_details(
            title,
            "Sincronización pausada temporalmente.\n"
            "Causa probable: Google Sheets aplicó límite de peticiones.\n"
            "Acción recomendada: Espera 1 minuto y pulsa Reintentar.",
            None,
            QMessageBox.Warning,
            action_buttons=(("Reintentar", retry_callback),),
        )
        return
    if isinstance(error, SheetsConfigError):
        show_message_with_details(
            title,
            "No se pudo sincronizar.\n"
            "Causa probable: Falta completar la configuración de Google Sheets.\n"
            "Acción recomendada: Abre configuración, guarda credenciales e ID de hoja, y reintenta.",
            None,
            QMessageBox.Warning,
            action_buttons=(("Ir a configuración", open_options_callback),),
        )
        return

    fallback_message = map_error_to_ui_message(error)
    show_message_with_details(
        title,
        fallback_message.as_text(),
        None,
        QMessageBox.Critical if fallback_message.severity == "blocking" else QMessageBox.Warning,
        action_buttons=(("Reintentar", retry_callback),),
    )


def handle_historico_render_mismatch(
    *,
    solicitudes: list[SolicitudDTO],
    row_count: int,
    table,
    model,
    proxy_model,
    apply_historico_filters: Callable[[], None],
    toast_error_callback: Callable[[str], None],
) -> int:
    """Extraído para encapsular recuperación de render y que la vista principal sea más legible."""
    if len(solicitudes) == 0 or row_count != 0:
        return row_count

    selection_model = table.selectionModel()
    logger.error(
        "UI_HISTORICO_DEBUG pre: widget=%s model=%s rowCount=%s sorting=%s updates=%s",
        type(table).__name__,
        type(table.model()).__name__ if table.model() is not None else None,
        row_count,
        table.isSortingEnabled(),
        table.updatesEnabled(),
    )
    logger.error("UI_HISTORICO_RENDER_MISMATCH count=%s row_count=%s", len(solicitudes), row_count)
    proxy_state = proxy_model.filter_state()
    logger.error(
        "UI_HISTORICO_PROXY_STATE ver_todas=%s delegada_id=%s year_mode=%s year=%s month=%s from=%s to=%s",
        proxy_state["ver_todas"],
        proxy_state["delegada_id"],
        proxy_state["year_mode"],
        proxy_state["year"],
        proxy_state["month"],
        proxy_state["from"],
        proxy_state["to"],
    )
    logger.error(
        "UI_HISTORICO_RENDER_RETRY source_rows=%s proxy_rows=%s selected_rows=%s",
        model.rowCount(),
        row_count,
        selection_model.selectedRows().__len__() if selection_model is not None else 0,
    )
    model.beginResetModel()
    model.endResetModel()
    model.layoutChanged.emit()
    apply_historico_filters()
    table.viewport().update()
    row_count = proxy_model.rowCount()
    logger.error("UI_HISTORICO_DEBUG post: expected=%s rowCount=%s", len(solicitudes), row_count)
    if row_count == 0:
        toast_error_callback("No se pudo renderizar el histórico (ver logs)")
    return row_count


def build_historico_filters_payload(*, delegada_id, estado, desde: str, hasta: str, search: str, force: bool, tab_index: int | None) -> dict[str, object]:
    """Helper pequeño para centralizar el snapshot de filtros usado en logs."""
    return {
        "delegada_id": delegada_id,
        "estado": estado,
        "desde": desde,
        "hasta": hasta,
        "search": search,
        "force": force,
        "tab_index": tab_index,
    }


def log_estado_pendientes(motivo: str, estado: dict[str, object]) -> None:
    logger.debug("estado_pendientes[%s]=%s", motivo, json.dumps(estado, ensure_ascii=False, default=str, indent=2))
