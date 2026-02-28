from __future__ import annotations

"""Catálogo centralizado de textos de interfaz.

Este módulo evita strings duplicados en widgets y facilita mantenimiento de copy.
Regla práctica para juniors:
- Usa claves estables por subcontexto (ej. ``solicitudes.*``).
- No referencies textos desde la UI de forma hardcoded.
- Si cambias un mensaje, conserva la clave y solo ajusta el valor.
"""

_COPY: dict[str, str] = {
    # Solicitudes
    "solicitudes.section_title": "Solicitudes",
    "solicitudes.subtitle": "Gestiona la operativa diaria de solicitudes con una vista clara y consistente.",
    "solicitudes.form_section_title": "Datos de la reserva",
    "solicitudes.label_delegada": "Delegada",
    "solicitudes.label_fecha": "Fecha",
    "solicitudes.label_desde": "Desde",
    "solicitudes.label_hasta": "Hasta",
    "solicitudes.label_notas": "Notas",
    "solicitudes.placeholder_notas": "Notas para la solicitud",
    "solicitudes.button_add_pending": "Añadir pendiente",
    "solicitudes.button_update_pending": "Actualizar pendiente",
    "solicitudes.button_confirm_without_pdf": "Confirmar sin PDF",
    "solicitudes.button_confirm_with_pdf": "Confirmar y generar PDF",
    "solicitudes.button_pending_delete": "Eliminar selección",
    "solicitudes.pending_errors_title": "Revisa estos puntos antes de continuar",
    "solicitudes.pending_errors_intro": "Falta completar algunos datos. Te indicamos cómo resolverlo:",
    "solicitudes.tooltip_delegada": "Selecciona la delegada para asociar correctamente la solicitud.",
    "solicitudes.tooltip_fecha": "Elige la fecha del permiso sindical que vas a registrar.",
    "solicitudes.tooltip_desde": "Hora de inicio. Ejemplo: 09:00.",
    "solicitudes.tooltip_hasta": "Hora de fin. Debe ser posterior a la hora de inicio.",
    "solicitudes.tooltip_minutos": "Duración calculada automáticamente en formato HH:MM.",
    "solicitudes.tooltip_notas": "Opcional: añade contexto para recordar el motivo.",
    "solicitudes.tip_enter": "Tip: pulsa Enter para guardar más rápido.",
    "solicitudes.tip_minutes": "Tip: 90 minutos equivalen a 1h 30min.",
    "solicitudes.tip_full_day": "Tip: marca 'Completo' cuando sea un día completo.",
    "solicitudes.help_toggle": "Mostrar ayuda",
    "solicitudes.status_ready": "Listo",
    "solicitudes.status_saved": "Guardado",
    "solicitudes.status_pending_sync": "Pendiente de sync",
    "solicitudes.status_error": "Error",
    "solicitudes.status_pending_sync_hint": "Hay cambios guardados localmente que aún no se han enviado a Google Sheets.",
    "solicitudes.validation_delegada": "Falta delegada. Selecciona una para continuar.",
    "solicitudes.validation_fecha": "Fecha inválida. Revisa el día seleccionado.",
    "solicitudes.validation_tramo_prefix": "Tramo horario incompleto.",
    "solicitudes.validation_conflict": "Ya existe un conflicto pendiente en esa fecha. Ajusta fecha o tramo.",
    "solicitudes.validation_blocking_toast": "Revisa los errores marcados y corrígelos para continuar.",
    "solicitudes.no_aplica_completo": "No aplica en solicitud completa",
    "solicitudes.confirm_delete_pending_title": "Confirmar eliminación",
    "solicitudes.confirm_delete_pending_message": "Se eliminará la solicitud pendiente seleccionada. ¿Deseas continuar?",
    # Sync credenciales
    "sync_credenciales.title": "Asistente de conexión con Google Sheets",
    "sync_credenciales.step_1": "Paso 1 · Qué necesitas",
    "sync_credenciales.step_1_body": "Necesitas el ID/URL de la hoja y un archivo JSON de credenciales de cuenta de servicio.",
    "sync_credenciales.step_2": "Paso 2 · Cargar credenciales",
    "sync_credenciales.step_3": "Paso 3 · Probar conexión",
    "sync_credenciales.step_4": "Paso 4 · Guardar y finalizar",
    "sync_credenciales.spreadsheet_placeholder": "Pega aquí la URL o el ID de la hoja",
    "sync_credenciales.credentials_button": "Seleccionar credenciales JSON…",
    "sync_credenciales.test_connection": "Probar conexión",
    "sync_credenciales.save": "Guardar",
    "sync_credenciales.saved_ok": "Configuración guardada. Ya puedes sincronizar.",
    "sync_credenciales.status_pending": "Pendiente de comprobación",
    "sync_credenciales.status_ok": "Conexión verificada",
    "sync_credenciales.status_credentials_missing": "Credenciales sin seleccionar",
    "sync_credenciales.status_credentials_ok": "Credenciales seleccionadas",
    "sync_credenciales.status_sheet_missing": "Hoja sin configurar",
    "sync_credenciales.status_sheet_ok": "Hoja configurada",
}


def copy_text(key: str) -> str:
    """Devuelve un texto de UI por clave estable.

    Lanza ``KeyError`` si falta la clave para detectar regresiones en tests.
    """

    return _COPY[key]


def copy_keys() -> tuple[str, ...]:
    """Expone las claves disponibles para validación en tests."""

    return tuple(_COPY.keys())
