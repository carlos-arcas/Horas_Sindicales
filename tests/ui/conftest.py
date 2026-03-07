import os
import sys
from ctypes.util import find_library
from pathlib import Path

import pytest

from app.application.dto import PersonaDTO
from app.testing.qt_harness import _humo_ui_estricto_activo, detectar_error_qt


def require_qt():
    # Este helper es exclusivo de tests UI: evita dependencia accidental en tests no-UI.
    caller_frame = sys._getframe(1)
    caller_file = Path(caller_frame.f_code.co_filename).as_posix()
    if "/tests/ui/" not in f"/{caller_file}":
        raise RuntimeError(
            "require_qt() solo debe usarse desde tests/ui/** para no "
            "acoplar tests no-UI al backend Qt."
        )

    error_qt = detectar_error_qt()
    if error_qt is not None:
        if _humo_ui_estricto_activo():
            raise RuntimeError(
                "PySide6 no disponible para smoke UI obligatorio en CI "
                f"(HORAS_UI_SMOKE_CI=1). {error_qt}"
            )
        pytest.skip(error_qt, allow_module_level=True)

    from PySide6.QtWidgets import QApplication

    return QApplication


def crear_persona_dto_valida(nombre: str) -> PersonaDTO:
    return PersonaDTO(
        id=None,
        nombre=nombre,
        genero="F",
        horas_mes=0,
        horas_ano=0,
        is_active=True,
        cuad_lun_man_min=0,
        cuad_lun_tar_min=0,
        cuad_mar_man_min=0,
        cuad_mar_tar_min=0,
        cuad_mie_man_min=0,
        cuad_mie_tar_min=0,
        cuad_jue_man_min=0,
        cuad_jue_tar_min=0,
        cuad_vie_man_min=0,
        cuad_vie_tar_min=0,
        cuad_sab_man_min=0,
        cuad_sab_tar_min=0,
        cuad_dom_man_min=0,
        cuad_dom_tar_min=0,
    )


def _is_ui_item(item: pytest.Item) -> bool:
    """True solo para tests cuyo path real cae dentro de tests/ui/**."""

    item_path = getattr(item, "path", None)
    if item_path is None:
        legacy_path = getattr(item, "fspath", None)
        if legacy_path is None:
            return False
        item_path = Path(str(legacy_path))

    normalized_parts = Path(str(item_path)).as_posix().split("/")
    for idx in range(len(normalized_parts) - 1):
        if normalized_parts[idx] == "tests" and normalized_parts[idx + 1] == "ui":
            return True
    return False


def _qt_ready() -> bool:
    """Chequeo mínimo y seguro para decidir si se deben coleccionar tests UI en CI."""

    if os.getenv("CI") != "true":
        return True

    display = os.getenv("DISPLAY", "").strip()
    platform = os.getenv("QT_QPA_PLATFORM", "").strip().lower()
    if not display and platform not in {"offscreen", "xcb"}:
        return False

    # Verificación opcional de librerías gráficas: no interrumpe ejecución.
    try:
        if not (find_library("EGL") or find_library("GL")):
            return False
    except Exception:
        pass

    return True


def pytest_collection_modifyitems(config, items):
    smoke_only_in_ci = os.getenv("CI") == "true" and os.getenv("RUN_UI_TESTS") != "1"
    smoke_only_allowlist = {
        "tests/ui/test_ui_arranque_minimo.py",
        "tests/ui/test_ui_navegacion_minima.py",
        "tests/ui/test_ui_headless_fallback_smoke.py",
        "tests/ui/test_confirmar_pdf_mainwindow_smoke.py",
        "tests/ui/test_pendientes_toasts_ci_smoke.py",
    }

    skip_non_smoke = pytest.mark.skip(
        reason="Modo smoke en CI: exporta RUN_UI_TESTS=1 para ejecutar toda la suite UI."
    )
    skip_ui_env = pytest.mark.skip(
        reason="Entorno UI no listo en CI (DISPLAY/QT_QPA_PLATFORM/librerías gráficas)."
    )

    qt_ready = _qt_ready()
    smoke_ui_estrictos = {
        "tests/ui/test_confirmar_pdf_mainwindow_smoke.py",
        "tests/ui/test_pendientes_toasts_ci_smoke.py",
    }

    for item in items:
        if not _is_ui_item(item):
            continue

        item_path = Path(str(getattr(item, "path", ""))).as_posix()
        es_smoke_ui_estricto = any(item_path.endswith(path) for path in smoke_ui_estrictos)

        if not qt_ready and not (_humo_ui_estricto_activo() and es_smoke_ui_estricto):
            item.add_marker(skip_ui_env)
            continue

        in_smoke_allowlist = any(item_path.endswith(path) for path in smoke_only_allowlist)
        if smoke_only_in_ci and not in_smoke_allowlist:
            item.add_marker(skip_non_smoke)
