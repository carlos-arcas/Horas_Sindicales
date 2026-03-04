from __future__ import annotations

from datetime import datetime

from app.domain.sync_models import SyncExecutionPlan, SyncFieldDiff, SyncPlanItem, SyncSummary
from app.ui.sync_reporting_builders import (
    build_conflicts,
    build_errors,
    build_simulation_entries,
    build_warnings,
)
from app.ui.sync_reporting_formatters import timestamp_y_duracion_simulacion
from app.ui.sync_reporting_orquestacion import build_sync_report


class _FakeDateTime:
    @staticmethod
    def fromisoformat(value: str) -> datetime:
        return datetime.fromisoformat(value)

    @staticmethod
    def now(tz=None) -> datetime:
        current = datetime.fromisoformat("2026-01-01T10:05:00+00:00")
        if tz is None:
            return current
        return current.astimezone(tz)


def test_builders_generan_listas_de_alertas() -> None:
    summary = SyncSummary(duplicates_skipped=2, omitted_by_delegada=1, conflicts_detected=1, errors=3)

    warnings = build_warnings(summary)
    errors = build_errors(summary)
    conflicts = build_conflicts(summary)

    assert len(warnings) == 2
    assert len(errors) == 1
    assert len(conflicts) == 1


def test_timestamp_y_duracion_simulacion_con_datetime_inyectable() -> None:
    now, duration_ms = timestamp_y_duracion_simulacion(
        "2026-01-01T10:00:00+00:00",
        datetime_provider=_FakeDateTime,
    )

    assert now == "2026-01-01T10:05:00+00:00"
    assert duration_ms == 300000


def test_build_simulation_entries_incluye_diffs_y_conflictos() -> None:
    plan = SyncExecutionPlan(
        generated_at="2026-01-01T10:00:00+00:00",
        worksheet="solicitudes",
        to_create=(SyncPlanItem(uuid="a1", action="create"),),
        to_update=(
            SyncPlanItem(
                uuid="b2",
                action="update",
                diffs=(SyncFieldDiff(field="estado", current_value="P", new_value="C"),),
            ),
        ),
        conflicts=(SyncPlanItem(uuid="c3", action="conflict", reason="duplicada"),),
        potential_errors=("fila inválida",),
    )

    entries = build_simulation_entries(plan, "2026-01-01T10:01:00+00:00")

    assert len(entries) == 5
    assert entries[0].severity == "INFO"
    assert entries[2].section == "Diff"
    assert entries[3].severity == "WARN"
    assert entries[4].suggested_action


def test_build_sync_report_calcula_retry_y_success_rate() -> None:
    summary = SyncSummary(inserted_local=2, updated_local=1, errors=1)

    report = build_sync_report(
        summary,
        status="OK",
        source="src",
        scope="all",
        actor="delegada",
    )

    assert report.counts["created"] == 2
    assert report.counts["updated"] == 1
    assert report.retry_count == 0
    assert report.success_rate == (2 / 3)
