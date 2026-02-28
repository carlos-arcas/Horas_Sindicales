from __future__ import annotations

import pytest

from app.application.sync_diagnostics import resolve_sync_diagnostic


@pytest.mark.parametrize(
    ("reason_code", "expected_title"),
    [
        ("file_not_found", "No encontramos el archivo"),
        ("permission_denied", "No hay permisos para leer el archivo"),
        ("invalid_credentials", "Credenciales no válidas"),
        ("sheet_access_denied", "Sin acceso a la hoja"),
        ("sheet_not_found", "No encontramos la hoja"),
        ("rate_limit", "Límite temporal de Google"),
        ("api_disabled", "API de Google Sheets desactivada"),
        ("missing_input", "Faltan datos por completar"),
        ("unknown", "No pudimos validar la conexión"),
        (None, "No pudimos validar la conexión"),
        ("", "No pudimos validar la conexión"),
        ("random", "No pudimos validar la conexión"),
        ("FILE_NOT_FOUND", "No pudimos validar la conexión"),
        ("sheet_not_foud", "No pudimos validar la conexión"),
        ("permissions", "No pudimos validar la conexión"),
        ("429", "No pudimos validar la conexión"),
        ("timeout", "No pudimos validar la conexión"),
        ("json", "No pudimos validar la conexión"),
        ("api", "No pudimos validar la conexión"),
        ("invalid", "No pudimos validar la conexión"),
        ("forbidden", "No pudimos validar la conexión"),
        ("not_found", "No pudimos validar la conexión"),
        ("denied", "No pudimos validar la conexión"),
        ("limit", "No pudimos validar la conexión"),
        ("missing", "No pudimos validar la conexión"),
    ],
)
def test_resolve_sync_diagnostic_titles(reason_code, expected_title):
    diagnostic = resolve_sync_diagnostic(reason_code)
    assert diagnostic.title == expected_title
    assert diagnostic.message
    assert diagnostic.suggested_action
    assert diagnostic.reason_code
