from __future__ import annotations

import importlib
import os

ARCHIVOS_SMOKE_UI_ESTRICTOS: tuple[str, ...] = (
    "tests/ui/test_confirmar_pdf_mainwindow_smoke.py",
    "tests/ui/test_pendientes_toasts_ci_smoke.py",
)

PLUGIN_PYTEST_QT: tuple[str, ...] = ("-p", "no:pytestqt", "-p", "no:pytestqt.plugin")
PLUGIN_PYTEST_COV: tuple[str, ...] = ("-p", "pytest_cov",)
ENV_PYTEST_CORE_NO_UI: tuple[tuple[str, str], ...] = (
    ("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1"),
    ("PYTEST_CORE_SIN_QT", "1"),
)


def _importar_modulo(nombre_modulo: str) -> None:
    importlib.import_module(nombre_modulo)


def _construir_args_pytest_core_no_ui(
    args_pytest: list[str], *, habilitar_pytest_cov: bool = False
) -> list[str]:
    prefijo_plugins: list[str] = [*PLUGIN_PYTEST_QT]
    if habilitar_pytest_cov:
        prefijo_plugins = [*PLUGIN_PYTEST_COV, *prefijo_plugins]
    return [*prefijo_plugins, *args_pytest]


def _construir_env_pytest_core_no_ui(
    entorno_base: dict[str, str] | None = None,
) -> dict[str, str]:
    entorno = dict(os.environ if entorno_base is None else entorno_base)
    for clave, valor in ENV_PYTEST_CORE_NO_UI:
        entorno[clave] = valor
    return entorno



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
