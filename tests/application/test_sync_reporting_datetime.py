import logging
from datetime import datetime

from app.domain.sync_models import SyncExecutionPlan
from app.ui import sync_reporting
from app.ui.sync_reporting import build_simulation_report


def _run_simulation_report_with_now(
    monkeypatch, *, now_iso: str, generated_at: str
) -> int:
    class FakeDateTime:
        @staticmethod
        def fromisoformat(value: str) -> datetime:
            return datetime.fromisoformat(value)

        @staticmethod
        def now(tz=None) -> datetime:
            current = datetime.fromisoformat(now_iso)
            if tz is None:
                return current
            if current.tzinfo is None:
                return current.replace(tzinfo=tz)
            return current.astimezone(tz)

    monkeypatch.setattr(sync_reporting, "datetime", FakeDateTime)
    plan = SyncExecutionPlan(generated_at=generated_at, worksheet="solicitudes")
    report = build_simulation_report(plan, source="src", scope="all", actor="delegada")
    return report.duration_ms


def test_simulation_report_duration_handles_now_naive_and_generated_aware(
    monkeypatch,
) -> None:
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


def test_simulation_report_duration_handles_now_aware_and_generated_naive(
    monkeypatch,
) -> None:
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


def test_simulation_report_no_crashea_si_generated_at_es_invalido(caplog) -> None:
    plan = SyncExecutionPlan(generated_at="iso-invalido", worksheet="solicitudes")

    with caplog.at_level(logging.WARNING):
        report = build_simulation_report(
            plan, source="src", scope="all", actor="delegada"
        )

    assert report.duration_ms == 0
    ultimo_log = caplog.records[-1]
    assert ultimo_log.evento == "sync_simulacion_iso_invalido"
    assert ultimo_log.generated_at == "iso-invalido"
    assert hasattr(ultimo_log, "now")
    assert not hasattr(ultimo_log, "plan")
