from __future__ import annotations

from dataclasses import dataclass

from app.application.use_cases.sync_sheets import SheetsSyncService
from app.domain.models import SheetsConfig


@dataclass
class _ConfigStore:
    def load(self) -> SheetsConfig:
        return SheetsConfig("sheet", "/tmp/cred.json", "device")


class _Client:
    def open_spreadsheet(self, *_args, **_kwargs):
        raise RuntimeError("No debería llamarse en estos tests")


class _Repository:
    def ensure_schema(self, *_args, **_kwargs):
        return []


def _service(connection) -> SheetsSyncService:
    return SheetsSyncService(connection, _ConfigStore(), _Client(), _Repository())


def test_dedupe_true_positive_con_normalizacion_hhmm(connection) -> None:
    service = _service(connection)
    row_a = {
        "delegada_uuid": "delegada-1",
        "fecha": "2024-01-15",
        "completo": 0,
        "minutos_total": "120",
        "desde_h": "09:00",
        "desde_m": "",
        "hasta_h": "11:00",
        "hasta_m": "",
    }
    row_b = {
        "delegada_uuid": "delegada-1",
        "fecha": "2024-01-15",
        "completo": 0,
        "minutos_total": 120,
        "desde_h": "9",
        "desde_m": "0",
        "hasta_h": "11",
        "hasta_m": "0",
    }
    assert service._solicitud_dedupe_key_from_remote_row(row_a) == service._solicitud_dedupe_key_from_remote_row(row_b)


def test_dedupe_false_positive_evita_colision_si_horas_difieren(connection) -> None:
    service = _service(connection)
    base = {
        "delegada_uuid": "delegada-1",
        "fecha": "2024-01-15",
        "completo": 0,
        "desde_h": "9",
        "desde_m": "0",
        "hasta_h": "11",
        "hasta_m": "0",
    }
    key_120 = service._solicitud_dedupe_key_from_remote_row({**base, "minutos_total": "120"})
    key_180 = service._solicitud_dedupe_key_from_remote_row({**base, "minutos_total": "180"})
    assert key_120 != key_180
