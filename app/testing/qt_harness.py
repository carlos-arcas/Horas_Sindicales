from __future__ import annotations

import importlib
import os

ARCHIVOS_SMOKE_UI_ESTRICTOS: tuple[str, ...] = (
    "tests/ui/test_confirmar_pdf_mainwindow_smoke.py",
    "tests/ui/test_pendientes_toasts_ci_smoke.py",
)


def _importar_modulo(nombre_modulo: str) -> None:
    importlib.import_module(nombre_modulo)


def _humo_ui_estricto_activo() -> bool:
    return os.getenv("HORAS_UI_SMOKE_CI") == "1"


def _es_humo_ui_estricto(nodeid: str) -> bool:
    if not _humo_ui_estricto_activo():
        return False
    return any(path in nodeid for path in ARCHIVOS_SMOKE_UI_ESTRICTOS)


def detectar_error_qt() -> str | None:
    """Retorna mensaje de error si Qt no puede importarse de forma utilizable."""

    try:
        _importar_modulo("PySide6")
        _importar_modulo("PySide6.QtCore")
        _importar_modulo("PySide6.QtWidgets")
        return None
    except Exception as exc:  # pragma: no cover - depende del runner
        mensaje = f"PySide6/Qt no disponible para tests UI: {exc}"
        if "libGL.so.1" in str(exc):
            mensaje += (
                " (falta dependencia nativa 'libGL.so.1'; "
                "instalar paquete de sistema equivalente a libgl1)"
            )
        return mensaje


def detectar_error_pytest_qt() -> str | None:
    """Retorna mensaje de error si pytest-qt no puede importarse de forma utilizable."""

    try:
        _importar_modulo("pytestqt")
        _importar_modulo("pytestqt.plugin")
        return None
    except Exception as exc:  # pragma: no cover - depende del runner
        return f"pytest-qt no disponible para tests UI con qtbot: {exc}"
