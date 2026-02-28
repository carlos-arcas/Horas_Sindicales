from __future__ import annotations

from typing import Any

from app.application.use_cases.sync_sheets import use_case as uc
from app.application.use_cases.sync_sheets.pull_planner import PullAction
from app.application.use_cases.sync_sheets.push_builder import PushBuildResult, PushConflict
from app.application.use_cases.sync_sheets.use_case import SheetsSyncService


class _Cursor:
    def __init__(self) -> None:
        self.rows: list[Any] = []

    def execute(self, *_: Any, **__: Any) -> None:
        return None

    def fetchall(self) -> list[Any]:
        return self.rows


class _Connection:
    def __init__(self) -> None:
        self._cursor = _Cursor()

    def cursor(self) -> _Cursor:
        return self._cursor

    def commit(self) -> None:
        return None


class _Config:
    spreadsheet_id = "s"
    credentials_path = "/tmp/c.json"
    device_id = "device-test"


class _ConfigStore:
    def load(self) -> _Config:
        return _Config()


class _Client:
    def open_spreadsheet(self, *_: Any) -> object:
        return object()

    def get_worksheets_by_title(self) -> dict[str, Any]:
        return {}


class _Repo:
    def ensure_schema(self, *_: Any) -> list[str]:
        return []


def _service() -> SheetsSyncService:
    return SheetsSyncService(connection=_Connection(), config_store=_ConfigStore(), client=_Client(), repository=_Repo())


def test_process_pull_row_calls_planner_and_runner(monkeypatch) -> None:
    service = _service()
    called: dict[str, Any] = {}

    monkeypatch.setattr(service, "build_pull_context", lambda dto: uc.PullContext(dto=dto, local_row=None))
    monkeypatch.setattr(service, "build_pull_signals", lambda *args, **kwargs: uc.PullSignals(False, False, False, False, False, False, None))

    def _fake_plan(signals: Any) -> tuple[PullAction, ...]:
        called["plan"] = signals
        return (PullAction("SKIP", "test_reason", {"counter": "omitted_duplicates"}),)

    def _fake_runner(actions: tuple[PullAction, ...], **handlers: Any) -> None:
        called["actions"] = actions
        handlers["on_skip"](actions[0])

    monkeypatch.setattr(uc, "plan_pull_actions", _fake_plan)
    monkeypatch.setattr(uc, "run_pull_actions", _fake_runner)

    stats = {"omitted_duplicates": 0}
    service._process_pull_solicitud_row(object(), [], 2, {"uuid": ""}, None, stats)

    assert called["actions"][0].reason_code == "test_reason"
    assert stats["omitted_duplicates"] == 1


def test_pull_solicitudes_worksheet_uses_savepoint_runner(monkeypatch) -> None:
    service = _service()
    monkeypatch.setattr(service, "_rows_with_index", lambda *args, **kwargs: ([], [(2, {"uuid": "u1"})]))
    monkeypatch.setattr(service, "_process_pull_solicitud_row", lambda *args, **kwargs: None)

    called = {"savepoint": ""}

    def _fake_savepoint(connection: Any, name: str, fn: Any) -> None:
        called["savepoint"] = name
        fn()

    monkeypatch.setattr(uc, "run_with_savepoint", _fake_savepoint)

    service._pull_solicitudes_worksheet("solicitudes", object(), None)
    assert called["savepoint"] == "pull_solicitudes_worksheet"


def test_push_solicitudes_calls_builder_and_runner(monkeypatch) -> None:
    service = _service()
    worksheet = object()
    monkeypatch.setattr(service, "_get_worksheet", lambda *args, **kwargs: worksheet)
    monkeypatch.setattr(service, "_rows_with_index", lambda *args, **kwargs: (uc.HEADER_CANONICO_SOLICITUDES, []))
    monkeypatch.setattr(service, "_uuid_index", lambda rows: {})
    monkeypatch.setattr(service, "_store_conflict", lambda *args, **kwargs: None)

    cursor = service._connection.cursor()
    cursor.rows = [{
        "uuid": "u1",
        "updated_at": "2024-01-01T00:00:00+00:00",
        "delegada_uuid": "d1",
        "delegada_nombre": "Delegada 1",
        "fecha_pedida": "2024-01-01",
        "desde_min": 60,
        "hasta_min": 120,
        "completo": 0,
        "horas_solicitadas_min": 60,
        "notas": "",
        "created_at": "2024-01-01T00:00:00+00:00",
        "source_device": "dev",
        "deleted": 0,
        "pdf_hash": "",
    }]

    captured = {"builder": False, "runner": False}

    original_builder = uc.build_push_solicitudes_payloads

    def _fake_builder(**kwargs: Any) -> Any:
        captured["builder"] = True
        return original_builder(**kwargs)

    def _fake_runner(ws: Any, values: Any, retries: int = 1) -> None:
        captured["runner"] = ws is worksheet and retries == 2 and len(values) >= 1

    monkeypatch.setattr(uc, "build_push_solicitudes_payloads", _fake_builder)
    monkeypatch.setattr(uc, "run_push_values_update", _fake_runner)

    service._push_solicitudes(object(), None)
    assert captured["builder"] is True
    assert captured["runner"] is True


def test_push_solicitudes_registers_conflicts_from_builder(monkeypatch) -> None:
    service = _service()
    monkeypatch.setattr(service, "_get_worksheet", lambda *args, **kwargs: object())
    monkeypatch.setattr(service, "_rows_with_index", lambda *args, **kwargs: (uc.HEADER_CANONICO_SOLICITUDES, []))
    monkeypatch.setattr(service, "_uuid_index", lambda rows: {})
    service._connection.cursor().rows = []
    monkeypatch.setattr(uc, "run_push_values_update", lambda *args, **kwargs: None)

    conflicts: list[str] = []
    monkeypatch.setattr(service, "_store_conflict", lambda table, uuid_value, *_: conflicts.append(f"{table}:{uuid_value}"))

    def _fake_builder(**_: Any) -> Any:
        return PushBuildResult(values=(("uuid",),), uploaded=0, omitted_duplicates=0, conflicts=(PushConflict(uuid_value="u-conf", local_row={}, remote_row={}),))

    monkeypatch.setattr(uc, "build_push_solicitudes_payloads", _fake_builder)

    service._push_solicitudes(object(), None)
    assert conflicts == ["solicitudes:u-conf"]


def test_pull_runner_wires_backfill_handler(monkeypatch) -> None:
    service = _service()
    hit = {"backfill": 0}
    monkeypatch.setattr(service, "_backfill_uuid", lambda *args, **kwargs: hit.__setitem__("backfill", 1))

    plan = (PullAction("BACKFILL_UUID", "backfill_existing_uuid", {"uuid": "abc"}),)
    stats = {}
    service._apply_pull_solicitud_plan(plan, object(), [], 2, {}, "", None, stats)

    assert hit["backfill"] == 1


def test_pull_skip_handler_ignores_missing_counter() -> None:
    service = _service()
    stats = {"omitted_duplicates": 0}
    service._apply_pull_solicitud_plan((PullAction("SKIP", "noop", {}),), object(), [], 2, {}, "", None, stats)
    assert stats["omitted_duplicates"] == 0


def test_use_case_parse_remote_row_calls_sync_snapshots(monkeypatch) -> None:
    called = {"ok": False}

    def _fake_parser(*args: Any, **kwargs: Any) -> Any:
        called["ok"] = True
        return uc.RemoteSolicitudRowDTO(row={"uuid": "u1"}, uuid_value="u1", remote_updated_at=None)

    monkeypatch.setattr(uc, "parse_remote_solicitud_row", _fake_parser)
    dto = SheetsSyncService.parse_remote_solicitud_row({"uuid": "u1"})

    assert called["ok"] is True
    assert dto.uuid_value == "u1"


def test_use_case_build_pull_signals_calls_sync_snapshots(monkeypatch) -> None:
    service = _service()
    dto = uc.RemoteSolicitudRowDTO(row={"uuid": ""}, uuid_value="", remote_updated_at=None)
    monkeypatch.setattr(service, "_find_solicitud_by_composite_key", lambda *_: None)
    monkeypatch.setattr(service, "_skip_pull_duplicate", lambda *args, **kwargs: False)
    called = {"ok": False}

    def _fake_build(*args: Any, **kwargs: Any) -> Any:
        called["ok"] = True
        return uc.PullSignals(False, False, False, False, False, True, None)

    monkeypatch.setattr(uc, "build_pull_signals_snapshot", _fake_build)
    signals = service.build_pull_signals(dto, None, None, {})
    assert called["ok"] is True
    assert signals.backfill_enabled is True


def test_use_case_pull_summary_tuple_order_contract() -> None:
    service = _service()
    stats = {"downloaded": 9, "conflicts": 8, "omitted_duplicates": 7, "omitted_by_delegada": 6, "errors": 5}
    assert uc.pull_stats_tuple(stats) == (9, 8, 7, 6, 5)


def test_use_case_skip_action_uses_reporting_counter(monkeypatch) -> None:
    service = _service()
    called = {"counter": ""}

    def _fake_apply(stats: dict[str, Any], *, counter: str) -> dict[str, Any]:
        called["counter"] = counter
        updated = dict(stats)
        updated[counter] = updated.get(counter, 0) + 1
        return updated

    monkeypatch.setattr(uc, "apply_stat_counter", _fake_apply)
    stats = {"omitted_duplicates": 0}
    service._apply_pull_solicitud_plan((PullAction("SKIP", "duplicate_without_uuid", {"counter": "omitted_duplicates"}),), object(), [], 2, {}, "", None, stats)
    assert called["counter"] == "omitted_duplicates"


def test_use_case_reason_code_text_contract_critical() -> None:
    assert uc.reason_text("conflict_divergent") == "Conflicto detectado: ambos lados cambiaron tras el último sync."
