from __future__ import annotations

import importlib
import os
import platform
from contextlib import contextmanager
from typing import Any, Iterator

ARCHIVOS_SMOKE_UI_ESTRICTOS: tuple[str, ...] = (
    "tests/ui/test_confirmar_pdf_mainwindow_smoke.py",
    "tests/ui/test_pendientes_toasts_ci_smoke.py",
)

PLUGIN_PYTEST_QT: tuple[str, ...] = ("-p", "no:pytestqt", "-p", "no:pytestqt.plugin")
PLUGIN_PYTEST_COV: tuple[str, ...] = (
    "-p",
    "pytest_cov",
)
ENV_PYTEST_CORE_NO_UI: tuple[tuple[str, str], ...] = (
    ("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1"),
    ("PYTEST_CORE_SIN_QT", "1"),
)
ENTORNO_QT_HEADLESS: tuple[tuple[str, str], ...] = (
    ("QT_QPA_PLATFORM", "offscreen"),
    ("QT_OPENGL", "software"),
    ("QT_QUICK_BACKEND", "software"),
)


def _importar_modulo(nombre_modulo: str) -> Any:
    return importlib.import_module(nombre_modulo)


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


@contextmanager
def _aplicar_entorno_pytest_core_no_ui() -> Iterator[None]:
    valores_previos: dict[str, str | None] = {
        clave: os.environ.get(clave) for clave, _ in ENV_PYTEST_CORE_NO_UI
    }
    for clave, valor in ENV_PYTEST_CORE_NO_UI:
        os.environ[clave] = valor
    try:
        yield
    finally:
        for clave, valor_previo in valores_previos.items():
            if valor_previo is None:
                os.environ.pop(clave, None)
            else:
                os.environ[clave] = valor_previo


def _humo_ui_estricto_activo() -> bool:
    return os.getenv("HORAS_UI_SMOKE_CI") == "1"


def _es_humo_ui_estricto(nodeid: str) -> bool:
    if not _humo_ui_estricto_activo():
        return False
    return any(path in nodeid for path in ARCHIVOS_SMOKE_UI_ESTRICTOS)


def preparar_entorno_qt_headless() -> dict[str, str]:
    """Prepara un entorno Qt razonable para CI/headless sin pisar overrides explícitos."""

    if platform.system() == "Linux":
        for clave, valor in ENTORNO_QT_HEADLESS:
            os.environ.setdefault(clave, valor)
    return {clave: os.environ.get(clave, "") for clave, _ in ENTORNO_QT_HEADLESS}


def _validar_modulos_qt_reales(qt_core: Any, qt_widgets: Any) -> str | None:
    qapplication = getattr(qt_widgets, "QApplication", None)
    if not hasattr(qapplication, "instance") or not callable(
        getattr(qapplication, "instance", None)
    ):
        return (
            "PySide6 importó pero QtWidgets.QApplication.instance no está disponible; "
            "posible stub/shadowing de Qt."
        )

    if getattr(qt_widgets, "QFileDialog", None) is None:
        return "PySide6 importó pero QtWidgets.QFileDialog no está disponible en este entorno."

    if getattr(qt_core, "QItemSelectionModel", None) is None:
        return "PySide6 importó pero QtCore.QItemSelectionModel no está disponible en este entorno."

    return None


def importar_qt_para_interfaz_real_o_omitir() -> tuple[Any, Any]:
    """Intenta preparar headless e importar Qt real; hace skip solo si sigue inutilizable."""

    preparar_entorno_qt_headless()

    try:
        qt_widgets = _importar_modulo("PySide6.QtWidgets")
        qt_core = _importar_modulo("PySide6.QtCore")
    except Exception as exc:  # pragma: no cover - depende del runner
        mensaje = (
            "PySide6/Qt no utilizable para test UI real incluso tras preparar modo headless "
            f"({exc})."
        )
        if "libGL.so.1" in str(exc):
            mensaje += " Falta dependencia nativa libGL.so.1/libgl1."
        import pytest

        pytest.skip(mensaje)

    error_validacion = _validar_modulos_qt_reales(qt_core, qt_widgets)
    if error_validacion is not None:
        import pytest

        pytest.skip(
            "PySide6 importó tras preparar modo headless, pero el backend Qt no es usable "
            f"para el flujo UI real: {error_validacion}"
        )

    return qt_widgets, qt_core


def detectar_error_qt() -> str | None:
    """Retorna mensaje de error si Qt no puede importarse de forma utilizable."""

    preparar_entorno_qt_headless()
    try:
        qt_core = _importar_modulo("PySide6.QtCore")
        qt_widgets = _importar_modulo("PySide6.QtWidgets")
    except Exception as exc:  # pragma: no cover - depende del runner
        mensaje = f"PySide6/Qt no disponible para tests UI: {exc}"
        if "libGL.so.1" in str(exc):
            mensaje += (
                " (falta dependencia nativa 'libGL.so.1'; "
                "instalar paquete de sistema equivalente a libgl1)"
            )
        return mensaje

    return _validar_modulos_qt_reales(qt_core, qt_widgets)


def detectar_error_pytest_qt() -> str | None:
    """Retorna mensaje de error si pytest-qt no puede importarse de forma utilizable."""

    try:
        _importar_modulo("pytestqt")
        _importar_modulo("pytestqt.plugin")
        return None
    except Exception as exc:  # pragma: no cover - depende del runner
        return f"pytest-qt no disponible para tests UI con qtbot: {exc}"
