import sqlite3
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.infrastructure.sheets_sync_service import SheetsSyncService


class _DummyConfigStore:
    def load(self) -> None:
        return None


class _DummyClient:
    pass


class _DummyRepository:
    pass


def _make_service() -> SheetsSyncService:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    return SheetsSyncService(connection, _DummyConfigStore(), _DummyClient(), _DummyRepository())


def test_no_duplicate_when_hours_differ() -> None:
    service = _make_service()
    row_base = {
        "delegada_uuid": "delegada-1",
        "fecha": "2024-01-15",
        "completo": 0,
        "desde_h": "9",
        "desde_m": "0",
        "hasta_h": "13",
        "hasta_m": "0",
    }
    key_one = service._solicitud_dedupe_key_from_remote_row(
        {**row_base, "minutos_total": "120"}
    )
    key_two = service._solicitud_dedupe_key_from_remote_row(
        {**row_base, "minutos_total": "180"}
    )
    assert key_one != key_two


def test_duplicate_when_time_is_normalized() -> None:
    service = _make_service()
    row_a = {
        "delegada_uuid": "delegada-1",
        "fecha": "2024-01-15",
        "completo": 0,
        "minutos_total": "120",
        "desde_h": "09:00",
        "desde_m": "",
        "hasta_h": "13:00",
        "hasta_m": "",
    }
    row_b = {
        "delegada_uuid": "delegada-1",
        "fecha": "2024-01-15",
        "completo": 0,
        "minutos_total": 120,
        "desde_h": "9",
        "desde_m": "0",
        "hasta_h": "13",
        "hasta_m": "0",
    }
    key_a = service._solicitud_dedupe_key_from_remote_row(row_a)
    key_b = service._solicitud_dedupe_key_from_remote_row(row_b)
    assert key_a == key_b


def test_completo_true_ignores_time_ranges() -> None:
    service = _make_service()
    row_a = {
        "delegada_uuid": "delegada-1",
        "fecha": "2024-01-15",
        "completo": 1,
        "minutos_total": 480,
        "desde_h": "08",
        "desde_m": "00",
        "hasta_h": "16",
        "hasta_m": "00",
    }
    row_b = {
        "delegada_uuid": "delegada-1",
        "fecha": "2024-01-15",
        "completo": 1,
        "minutos_total": 480,
        "desde_h": "10",
        "desde_m": "00",
        "hasta_h": "18",
        "hasta_m": "00",
    }
    key_a = service._solicitud_dedupe_key_from_remote_row(row_a)
    key_b = service._solicitud_dedupe_key_from_remote_row(row_b)
    assert key_a == key_b
