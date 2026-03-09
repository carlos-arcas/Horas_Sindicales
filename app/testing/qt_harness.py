from __future__ import annotations

import importlib
import os
from contextlib import contextmanager
from typing import Iterator

ARCHIVOS_SMOKE_UI_ESTRICTOS: tuple[str, ...] = (
    "tests/ui/test_confirmar_pdf_mainwindow_smoke.py",
    "tests/ui/test_pendientes_toasts_ci_smoke.py",
)

PLUGIN_PYTEST_QT: tuple[str, ...] = ("-p", "no:pytestqt", "-p", "no:pytestqt.plugin")
VARIABLES_ENTORNO_PYTEST_CORE: tuple[tuple[str, str], ...] = (
    ("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1"),
    ("PYTEST_CORE_SIN_QT", "1"),
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


def _construir_entorno_ejecucion_pytest_core(
    entorno_base: dict[str, str] | None = None,
    *,
    activar_pytest_cov: bool = False,
) -> dict[str, str]:
    entorno = dict(entorno_base or os.environ)
    for nombre_variable, valor in VARIABLES_ENTORNO_PYTEST_CORE:
        entorno[nombre_variable] = valor
    if activar_pytest_cov:
        plugins_existentes = entorno.get("PYTEST_PLUGINS", "").strip()
        plugins = [plugin for plugin in plugins_existentes.split(",") if plugin]
        if "pytest_cov" not in plugins:
            plugins.append("pytest_cov")
        entorno["PYTEST_PLUGINS"] = ",".join(plugins)
    return entorno


@contextmanager
def _contexto_entorno_pytest_core(
    *, activar_pytest_cov: bool = False
) -> Iterator[None]:
    respaldo = {
        nombre_variable: os.environ.get(nombre_variable)
        for nombre_variable, _ in VARIABLES_ENTORNO_PYTEST_CORE
    }
    respaldo_plugins = os.environ.get("PYTEST_PLUGINS")
    try:
        for nombre_variable, valor in VARIABLES_ENTORNO_PYTEST_CORE:
            os.environ[nombre_variable] = valor
        if activar_pytest_cov:
            plugins_existentes = os.environ.get("PYTEST_PLUGINS", "").strip()
            plugins = [plugin for plugin in plugins_existentes.split(",") if plugin]
            if "pytest_cov" not in plugins:
                plugins.append("pytest_cov")
            os.environ["PYTEST_PLUGINS"] = ",".join(plugins)
        yield
    finally:
        for nombre_variable, _ in VARIABLES_ENTORNO_PYTEST_CORE:
            valor_original = respaldo[nombre_variable]
            if valor_original is None:
                os.environ.pop(nombre_variable, None)
            else:
                os.environ[nombre_variable] = valor_original
        if respaldo_plugins is None:
            os.environ.pop("PYTEST_PLUGINS", None)
        else:
            os.environ["PYTEST_PLUGINS"] = respaldo_plugins
