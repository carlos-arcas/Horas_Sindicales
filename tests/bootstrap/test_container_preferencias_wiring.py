from __future__ import annotations

import importlib
from pathlib import Path

import pytest

from app.bootstrap import container as container_module
from app.bootstrap.container import build_container
from app.infrastructure.db import get_connection
from app.infrastructure.local_config import RepositorioPreferenciasIni

pytestmark = pytest.mark.ui


def _connection_factory(tmp_path: Path):
    db_path = tmp_path / "preferencias_wiring.db"

    def _factory():
        return get_connection(db_path)

    return _factory


def test_build_container_usa_fallback_ini_si_qsettings_no_esta(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    original_import_module = importlib.import_module

    def _import_module(name: str, package: str | None = None):
        if name == "infraestructura.repositorio_preferencias_qsettings":
            raise ImportError("QSettings no disponible")
        return original_import_module(name, package)

    monkeypatch.setattr(container_module.importlib, "import_module", _import_module)

    with caplog.at_level("WARNING"):
        container = build_container(connection_factory=_connection_factory(tmp_path), preferencias_headless=False)

    assert isinstance(container.repositorio_preferencias, RepositorioPreferenciasIni)
    assert "persistencia headless INI" in caplog.text


def test_build_container_usa_qsettings_si_esta_disponible(tmp_path: Path) -> None:
    modulo = pytest.importorskip("infraestructura.repositorio_preferencias_qsettings")
    if not hasattr(modulo, "RepositorioPreferenciasQSettings"):
        pytest.skip("No existe RepositorioPreferenciasQSettings en el entorno actual")

    container = build_container(connection_factory=_connection_factory(tmp_path), preferencias_headless=False)

    assert (
        container.repositorio_preferencias.__class__.__name__
        == "RepositorioPreferenciasQSettings"
    )
