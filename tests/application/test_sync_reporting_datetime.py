from datetime import datetime

from app.domain.sync_models import SyncExecutionPlan
from app.ui import sync_reporting
from app.ui.sync_reporting import build_simulation_report


def _run_simulation_report_with_now(monkeypatch, *, now_iso: str, generated_at: str) -> int:
    class FakeDateTime:
        @staticmethod
        def fromisoformat(value: str) -> datetime:
            return datetime.fromisoformat(value)

        @staticmethod
        def now() -> datetime:
            return datetime.fromisoformat(now_iso)

    monkeypatch.setattr(sync_reporting, "datetime", FakeDateTime)
    plan = SyncExecutionPlan(generated_at=generated_at, worksheet="solicitudes")
    report = build_simulation_report(plan, source="src", scope="all", actor="delegada")
    return report.duration_ms


def test_simulation_report_duration_handles_now_naive_and_generated_aware(monkeypatch) -> None:
    duration_ms = _run_simulation_report_with_now(
        monkeypatch,
        now_iso="2026-01-01T10:01:00",
        generated_at="2026-01-01T10:00:00+00:00",
    )
    assert duration_ms >= 0


def test_simulation_report_duration_handles_both_naive(monkeypatch) -> None:
    duration_ms = _run_simulation_report_with_now(
        monkeypatch,
        now_iso="2026-01-01T10:01:00",
        generated_at="2026-01-01T10:00:00",
    )
    assert duration_ms >= 0


def test_simulation_report_duration_handles_both_aware(monkeypatch) -> None:
    duration_ms = _run_simulation_report_with_now(
        monkeypatch,
        now_iso="2026-01-01T10:01:00+00:00",
        generated_at="2026-01-01T10:00:00+00:00",
    )
    assert duration_ms >= 0


def test_simulation_report_duration_handles_now_aware_and_generated_naive(monkeypatch) -> None:
    duration_ms = _run_simulation_report_with_now(
        monkeypatch,
        now_iso="2026-01-01T10:01:00+00:00",
        generated_at="2026-01-01T10:00:00",
    )
    assert duration_ms >= 0


def test_simulation_report_duration_handles_aware_offsets(monkeypatch) -> None:
    duration_ms = _run_simulation_report_with_now(
        monkeypatch,
        now_iso="2026-01-01T10:01:00+02:00",
        generated_at="2026-01-01T09:59:30+00:00",
    )
    assert duration_ms >= 0



def test_simulation_report_iso_invalido_no_rompe_ui_y_log_minimo(caplog) -> None:
    plan = SyncExecutionPlan(generated_at="no-es-iso", worksheet="solicitudes")
    with caplog.at_level("WARNING"):
        report = build_simulation_report(plan, source="src", scope="all", actor="delegada")

    assert report.duration_ms == 0
    warning = next(record for record in caplog.records if record.msg == "No se pudo calcular duración por ISO inválido; se devuelve 0.")
    payload = warning.extra
    assert payload["generated_at"] == "no-es-iso"
    assert "now" in payload
    assert set(payload.keys()) == {"evento", "generated_at", "now"}


def test_parsear_iso_naive_registra_normalizacion_tz_local(caplog) -> None:
    with caplog.at_level("INFO"):
        sync_reporting._parsear_iso_utc_aware("2026-01-01T10:00:00")

    info = next(
        record
        for record in caplog.records
        if record.msg == "ISO naive normalizado a zona horaria local para reporte de sincronización."
    )
    payload = info.extra
    assert payload["evento"] == "sync_report_tz_naive_normalizado"
    assert payload["valor_iso"] == "2026-01-01T10:00:00"
    assert payload["tz_local"]
