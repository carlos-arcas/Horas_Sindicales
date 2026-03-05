from __future__ import annotations

import os
import platform
import sqlite3
import sys
from importlib.abc import MetaPathFinder
from importlib.machinery import ModuleSpec
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _is_linux_headless() -> bool:
    if platform.system() != "Linux":
        return False
    return not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))


if _is_linux_headless():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    os.environ.setdefault("QT_OPENGL", "software")


_UI_BACKEND_ERROR: str | None = None


class _PySide6Blocker(MetaPathFinder):
    def find_spec(self, fullname: str, path: object | None, target: object | None = None) -> ModuleSpec | None:
        if fullname == "PySide6" or fullname.startswith("PySide6."):
            raise ImportError("PySide6 bloqueado en ejecución core (pytest -m 'not ui').")
        return None


def _is_ui_execution(config: pytest.Config) -> bool:
    markexpr = (config.option.markexpr or "").strip()
    if "ui" in markexpr and "not ui" not in markexpr:
        return True

    normalized_args = [Path(str(arg)).as_posix() for arg in getattr(config, "args", [])]
    return any(
        arg == "tests/ui"
        or arg.endswith("/tests/ui")
        or arg.endswith("/tests/ui/")
        or "/tests/ui/" in f"/{arg}"
        for arg in normalized_args
    )


def _core_qt_block_enabled(config: pytest.Config) -> bool:
    markexpr = (config.option.markexpr or "").strip()
    core_only = "not ui" in markexpr or os.getenv("PYTEST_CORE_SIN_QT") == "1"
    return core_only and not _is_ui_execution(config)


def _enforce_core_without_qt(config: pytest.Config) -> None:
    if not _core_qt_block_enabled(config):
        return
    for module_name in [name for name in list(sys.modules) if name == "PySide6" or name.startswith("PySide6.")]:
        sys.modules.pop(module_name, None)
    if not any(isinstance(finder, _PySide6Blocker) for finder in sys.meta_path):
        sys.meta_path.insert(0, _PySide6Blocker())


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "ui: tests de interfaz PySide6")
    config.addinivalue_line("markers", "headless_safe: test UI que no requiere backend Qt")
    config.addinivalue_line("markers", "metrics: tests de métricas/calidad (radon opcional)")
    config.addinivalue_line("markers", "smoke: pruebas smoke rápidas y deterministas")
    config.addinivalue_line("markers", "e2e: pruebas end-to-end sin UI real")
    _enforce_core_without_qt(config)


def pytest_ignore_collect(collection_path: Path, config: pytest.Config) -> bool:
    if not _core_qt_block_enabled(config):
        return False
    relative_path = collection_path.as_posix()
    blocked_paths = (
        "/tests/ui/",
        "/tests/presentacion/",
        "/tests/test_ui_structure.py",
        "/tests/entrypoints/test_arranque_worker.py",
        "/tests/infrastructure/test_repositorio_preferencias_qsettings.py",
    )
    normalized_path = f"/{relative_path}"
    return any(token in normalized_path for token in blocked_paths) or relative_path.endswith(("/tests/ui", "/tests/presentacion"))


def _detect_ui_backend_issue() -> str | None:
    try:
        import importlib

        importlib.import_module("PySide6")
        importlib.import_module("PySide6.QtWidgets")
        return None
    except Exception as exc:  # pragma: no cover - depende del host de ejecución
        return f"PySide6/Qt no disponible para tests UI: {exc}"


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    global _UI_BACKEND_ERROR
    skip_ui = None
    core_only_run = _core_qt_block_enabled(config)
    has_ui_items = any("tests/ui/" in item.nodeid or item.get_closest_marker("ui") is not None for item in items)
    if has_ui_items and not core_only_run and _UI_BACKEND_ERROR is None:
        _UI_BACKEND_ERROR = _detect_ui_backend_issue()
    if _UI_BACKEND_ERROR is not None:
        skip_ui = pytest.mark.skip(reason=_UI_BACKEND_ERROR)

    for item in items:
        if "tests/ui/" in item.nodeid and "headless_safe" not in item.keywords:
            item.add_marker(pytest.mark.ui)
        if skip_ui is not None and item.get_closest_marker("ui") is not None:
            item.add_marker(skip_ui)

    guard_nodeid = "tests/test_000_no_qt_in_core.py::test_core_suite_no_importa_pyside6"
    guard_items = [item for item in items if item.nodeid.endswith(guard_nodeid)]
    if guard_items:
        items[:] = guard_items + [item for item in items if item not in guard_items]


from app.application.dto import SolicitudDTO
from app.application.use_cases import PersonaUseCases, SolicitudUseCases
from app.domain.models import Persona
from app.infrastructure.migrations import run_migrations
from app.infrastructure.repos_sqlite import RepositorioPersonasSQLite, SolicitudRepositorySQLite


@pytest.fixture
def connection() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    run_migrations(conn)
    yield conn
    conn.close()


@pytest.fixture
def persona_repo(connection: sqlite3.Connection) -> RepositorioPersonasSQLite:
    return RepositorioPersonasSQLite(connection)


@pytest.fixture
def solicitud_repo(connection: sqlite3.Connection) -> SolicitudRepositorySQLite:
    return SolicitudRepositorySQLite(connection)


@pytest.fixture
def solicitud_use_cases(
    solicitud_repo: SolicitudRepositorySQLite,
    persona_repo: RepositorioPersonasSQLite,
) -> SolicitudUseCases:
    return SolicitudUseCases(solicitud_repo, persona_repo)




@pytest.fixture
def persona_use_cases(persona_repo: RepositorioPersonasSQLite) -> PersonaUseCases:
    return PersonaUseCases(persona_repo)


@pytest.fixture
def persona_id(persona_repo: RepositorioPersonasSQLite) -> int:
    persona = persona_repo.create(
        Persona(
            id=None,
            nombre="Delegada Fixture",
            genero="F",
            horas_mes_min=600,
            horas_ano_min=7200,
            is_active=True,
            cuad_lun_man_min=240,
            cuad_lun_tar_min=240,
            cuad_mar_man_min=240,
            cuad_mar_tar_min=240,
            cuad_mie_man_min=240,
            cuad_mie_tar_min=240,
            cuad_jue_man_min=240,
            cuad_jue_tar_min=240,
            cuad_vie_man_min=240,
            cuad_vie_tar_min=240,
            cuad_sab_man_min=0,
            cuad_sab_tar_min=0,
            cuad_dom_man_min=0,
            cuad_dom_tar_min=0,
        )
    )
    return int(persona.id or 0)


@pytest.fixture
def solicitud_dto(persona_id: int) -> SolicitudDTO:
    return SolicitudDTO(
        id=None,
        persona_id=persona_id,
        fecha_solicitud="2025-01-01",
        fecha_pedida="2025-01-15",
        desde="09:00",
        hasta="11:00",
        completo=False,
        horas=2.0,
        observaciones="Obs",
        pdf_path=None,
        pdf_hash=None,
        notas="Nota",
    )
