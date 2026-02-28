from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SyncDiagnostic:
    reason_code: str
    title: str
    message: str
    suggested_action: str


_REASON_MAP: dict[str, SyncDiagnostic] = {
    "file_not_found": SyncDiagnostic(
        reason_code="file_not_found",
        title="No encontramos el archivo",
        message="No se encontró el archivo de credenciales en la ruta indicada.",
        suggested_action="Selecciona de nuevo el archivo JSON y vuelve a probar.",
    ),
    "permission_denied": SyncDiagnostic(
        reason_code="permission_denied",
        title="No hay permisos para leer el archivo",
        message="La app no puede leer el archivo de credenciales por permisos del sistema.",
        suggested_action="Revisa permisos del archivo o elige una copia en tu carpeta de usuario.",
    ),
    "invalid_credentials": SyncDiagnostic(
        reason_code="invalid_credentials",
        title="Credenciales no válidas",
        message="El archivo de credenciales no es válido para Google Sheets.",
        suggested_action="Descarga un JSON de cuenta de servicio correcto y vuelve a cargarlo.",
    ),
    "sheet_access_denied": SyncDiagnostic(
        reason_code="sheet_access_denied",
        title="Sin acceso a la hoja",
        message="La cuenta de servicio no tiene acceso a la hoja indicada.",
        suggested_action="Comparte la hoja con el email de la cuenta de servicio como Editor.",
    ),
    "sheet_not_found": SyncDiagnostic(
        reason_code="sheet_not_found",
        title="No encontramos la hoja",
        message="El ID o URL de la hoja no corresponde a una hoja accesible.",
        suggested_action="Revisa el ID/URL y prueba de nuevo.",
    ),
    "rate_limit": SyncDiagnostic(
        reason_code="rate_limit",
        title="Límite temporal de Google",
        message="Google Sheets aplicó un límite temporal de peticiones.",
        suggested_action="Espera 1 minuto y vuelve a intentar la prueba.",
    ),
    "api_disabled": SyncDiagnostic(
        reason_code="api_disabled",
        title="API de Google Sheets desactivada",
        message="La API de Google Sheets no está habilitada en tu proyecto.",
        suggested_action="Activa la API en Google Cloud y reintenta en unos minutos.",
    ),
    "missing_input": SyncDiagnostic(
        reason_code="missing_input",
        title="Faltan datos por completar",
        message="Falta el ID/URL de la hoja o el archivo de credenciales.",
        suggested_action="Completa ambos campos y pulsa 'Probar conexión'.",
    ),
    "unknown": SyncDiagnostic(
        reason_code="unknown",
        title="No pudimos validar la conexión",
        message="Ocurrió un error inesperado durante la comprobación.",
        suggested_action="Revisa los datos y vuelve a intentarlo. Si persiste, contacta soporte.",
    ),
}


def resolve_sync_diagnostic(reason_code: str | None) -> SyncDiagnostic:
    if not reason_code:
        return _REASON_MAP["unknown"]
    return _REASON_MAP.get(reason_code, _REASON_MAP["unknown"])
