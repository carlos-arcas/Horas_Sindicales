from __future__ import annotations

from app.application.use_cases import sync_sheets
from app.application.use_cases.sync_sheets import HEADER_CANONICO_SOLICITUDES
from app.application.use_cases.sync_sheets import SheetsSyncService


def test_facade_exporta_api_publica_minima() -> None:
    assert sorted(sync_sheets.__all__) == ["HEADER_CANONICO_SOLICITUDES", "SheetsSyncService"]


def test_facade_reexporta_objetos_reales() -> None:
    assert sync_sheets.HEADER_CANONICO_SOLICITUDES is HEADER_CANONICO_SOLICITUDES
    assert sync_sheets.SheetsSyncService is SheetsSyncService

