from __future__ import annotations

from app.domain.sync_models import SyncExecutionPlan
from app.infrastructure.sync_sheets_adapter import SyncSheetsAdapter


class _Conn:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


class _ServiceFake:
    def __init__(self, _conn, _config, _client, _repo) -> None:
        self.calls: list[tuple[str, tuple[object, ...]]] = []

    def store_sync_config_value(self, key: str, value: str) -> None:
        self.calls.append(("store_sync_config_value", (key, value)))

    def execute_sync_plan(self, plan):
        self.calls.append(("execute_sync_plan", (plan,)))
        return "done"


def test_adapter_normaliza_store_sync_config_y_cierra_conexion(monkeypatch) -> None:
    conn = _Conn()
    service = _ServiceFake(None, None, None, None)

    monkeypatch.setattr("app.infrastructure.sync_sheets_adapter.SheetsSyncService", lambda *args: service)
    adapter = SyncSheetsAdapter(lambda: conn, object(), object(), object())

    adapter.store_sync_config_value(" token ", "  valor ")

    assert service.calls == [("store_sync_config_value", ("token", "valor"))]
    assert conn.closed is True


def test_adapter_execute_sync_plan_valida_shape(monkeypatch) -> None:
    conn = _Conn()
    service = _ServiceFake(None, None, None, None)
    monkeypatch.setattr("app.infrastructure.sync_sheets_adapter.SheetsSyncService", lambda *args: service)
    adapter = SyncSheetsAdapter(lambda: conn, object(), object(), object())

    plan = SyncExecutionPlan(generated_at="hoy", worksheet="solicitudes")
    assert adapter.execute_sync_plan(plan) == "done"
    assert service.calls[0][0] == "execute_sync_plan"
