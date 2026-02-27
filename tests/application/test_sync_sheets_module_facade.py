from __future__ import annotations

import importlib.util
from pathlib import Path

from app.application.use_cases import sync_sheets
from app.application.use_cases.sync_sheets import HEADER_CANONICO_SOLICITUDES
from app.application.use_cases.sync_sheets import SheetsSyncService


def test_facade_exporta_api_publica_minima() -> None:
    assert sorted(sync_sheets.__all__) == ["HEADER_CANONICO_SOLICITUDES", "SheetsSyncService"]


def test_facade_reexporta_objetos_reales() -> None:
    assert sync_sheets.HEADER_CANONICO_SOLICITUDES is HEADER_CANONICO_SOLICITUDES
    assert sync_sheets.SheetsSyncService is SheetsSyncService


def test_compat_facade_legado_expone_los_mismos_simbolos() -> None:
    modulo_path = Path(__file__).resolve().parents[2] / "app/application/use_cases/sync_sheets.py"
    spec = importlib.util.spec_from_file_location("tests.sync_sheets_legacy_facade", modulo_path)
    assert spec and spec.loader
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)

    assert modulo.__all__ == ["HEADER_CANONICO_SOLICITUDES", "SheetsSyncService"]
    assert modulo.HEADER_CANONICO_SOLICITUDES is HEADER_CANONICO_SOLICITUDES
    assert modulo.SheetsSyncService is SheetsSyncService
