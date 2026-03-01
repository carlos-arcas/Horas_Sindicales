from datetime import datetime, timezone

from app.domain.sync_models import SyncExecutionPlan
from app.ui import sync_reporting


class _FechaNaive:
    @classmethod
    def now(cls) -> datetime:
        return datetime(2025, 1, 10, 12, 0, 1)


class _FechaAware:
    @classmethod
    def now(cls) -> datetime:
        return datetime(2025, 1, 10, 12, 0, 1, tzinfo=timezone.utc)


def _plan(generated_at: str) -> SyncExecutionPlan:
    return SyncExecutionPlan(generated_at=generated_at, worksheet="Hoja 1")


def test_build_simulation_report_no_falla_con_now_naive_y_plan_aware(monkeypatch) -> None:
    monkeypatch.setattr(sync_reporting, "datetime", _FechaNaive)

    reporte = sync_reporting.build_simulation_report(
        _plan("2025-01-10T12:00:00+00:00"),
        source="sheet",
        scope="all",
        actor="delegada",
    )

    assert isinstance(reporte.duration_ms, int)
    assert reporte.duration_ms >= 0


def test_build_simulation_report_no_falla_con_now_aware_y_plan_naive(monkeypatch) -> None:
    monkeypatch.setattr(sync_reporting, "datetime", _FechaAware)

    reporte = sync_reporting.build_simulation_report(
        _plan("2025-01-10T12:00:00"),
        source="sheet",
        scope="all",
        actor="delegada",
    )

    assert isinstance(reporte.duration_ms, int)
    assert reporte.duration_ms >= 0
