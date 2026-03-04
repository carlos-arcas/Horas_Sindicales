from __future__ import annotations

import uuid
from dataclasses import replace
from datetime import datetime

from app.domain.sync_models import (
    SyncAttemptReport,
    SyncExecutionPlan,
    SyncLogEntry,
    SyncReport,
    SyncSummary,
)
from app.ui.sync_reporting_builders import (
    build_conflicts,
    build_errors,
    build_simulation_entries,
    build_warnings,
    calcular_tasa_exito,
)
from app.ui.sync_reporting_formatters import (
    build_base_entries,
    duracion_ms_entre_isos,
    timestamp_y_duracion_simulacion,
    txt,
)


def build_sync_report(
    summary: SyncSummary,
    *,
    status: str,
    source: str,
    scope: str,
    actor: str,
    details: str | None = None,
    started_at: str | None = None,
    sync_id: str | None = None,
    attempt_history: tuple[SyncAttemptReport, ...] = (),
    rows_total_local: int = 0,
    rows_scanned_remote: int = 0,
    api_calls_count: int = 0,
) -> SyncReport:
    started = started_at or datetime.now().isoformat()
    finished = datetime.now().isoformat()
    warnings = build_warnings(summary)
    errors = build_errors(summary)
    conflicts = build_conflicts(summary)
    entries = build_base_entries(
        inserted_local=summary.inserted_local,
        updated_local=summary.updated_local,
        inserted_remote=summary.inserted_remote,
        updated_remote=summary.updated_remote,
        warnings=warnings,
        errors=errors,
        conflicts=conflicts,
        details=details,
        finished=finished,
    )
    attempts = max(1, len(attempt_history) or 1)
    total_operations = (
        summary.inserted_local
        + summary.updated_local
        + summary.inserted_remote
        + summary.updated_remote
    )
    success_rate = calcular_tasa_exito(total_operations, summary.errors)
    return SyncReport(
        sync_id=sync_id or str(uuid.uuid4()),
        started_at=started,
        finished_at=finished,
        attempts=attempts,
        final_status=status,
        status=status,
        source=source,
        scope=scope,
        idempotency_criteria=txt("ui.sync_report.idempotency_criteria"),
        actor=actor,
        counts={
            "created": summary.inserted_local + summary.inserted_remote,
            "updated": summary.updated_local + summary.updated_remote,
            "skipped": summary.duplicates_skipped + summary.omitted_by_delegada,
            "conflicts": summary.conflicts_detected,
            "errors": summary.errors,
        },
        warnings=warnings,
        errors=errors,
        conflicts=conflicts,
        items_changed=[
            txt(
                "ui.sync_report.items_changed_local",
                created=summary.inserted_local,
                updated=summary.updated_local,
            ),
            txt(
                "ui.sync_report.items_changed_sheets",
                created=summary.inserted_remote,
                updated=summary.updated_remote,
            ),
        ],
        entries=entries,
        duration_ms=duracion_ms_entre_isos(started, finished),
        rows_total_local=rows_total_local,
        rows_scanned_remote=rows_scanned_remote,
        api_calls_count=api_calls_count,
        retry_count=max(0, attempts - 1),
        conflicts_count=summary.conflicts_detected,
        error_count=summary.errors,
        success_rate=success_rate,
        attempt_history=attempt_history
        or (
            SyncAttemptReport(
                attempt_number=1,
                status=status,
                created=summary.inserted_local + summary.inserted_remote,
                updated=summary.updated_local + summary.updated_remote,
                conflicts=summary.conflicts_detected,
                errors=summary.errors,
            ),
        ),
    )


def build_config_incomplete_report(source: str, scope: str, actor: str) -> SyncReport:
    report = SyncReport.empty()
    now = datetime.now().isoformat()
    return replace(
        report,
        sync_id=str(uuid.uuid4()),
        started_at=now,
        finished_at=now,
        attempts=1,
        final_status="CONFIG_INCOMPLETE",
        status="CONFIG_INCOMPLETE",
        source=source,
        scope=scope,
        actor=actor,
        entries=[
            SyncLogEntry(
                timestamp=now,
                severity="ERROR",
                section=txt("ui.sync_report.section_operacion"),
                entity=txt("ui.sync_report.entity_config"),
                message=txt("ui.sync_report.error_falta_config"),
                suggested_action=txt("ui.sync_report.sugerencia_ir_config"),
            )
        ],
        errors=[txt("ui.sync_report.error_config_incompleta")],
        counts={"created": 0, "updated": 0, "skipped": 0, "conflicts": 0, "errors": 1},
        error_count=1,
        success_rate=0.0,
    )


def build_failed_report(
    error_message: str,
    *,
    source: str,
    scope: str,
    actor: str,
    details: str | None,
    started_at: str | None,
    sync_id: str | None = None,
    attempt_history: tuple[SyncAttemptReport, ...] = (),
) -> SyncReport:
    start = started_at or datetime.now().isoformat()
    now = datetime.now().isoformat()
    return SyncReport(
        sync_id=sync_id or str(uuid.uuid4()),
        started_at=start,
        finished_at=now,
        attempts=max(1, len(attempt_history) or 1),
        final_status="ERROR",
        status="ERROR",
        source=source,
        scope=scope,
        idempotency_criteria=txt("ui.sync_report.idempotency_criteria"),
        actor=actor,
        counts={"created": 0, "updated": 0, "skipped": 0, "conflicts": 0, "errors": 1},
        errors=[error_message],
        entries=[
            SyncLogEntry(
                timestamp=now,
                severity="ERROR",
                section=txt("ui.sync_report.section_errores"),
                entity=txt("ui.sync_report.entity_red"),
                message=error_message,
                suggested_action=txt("ui.sync_report.sugerencia_revisar_config_red"),
            ),
            SyncLogEntry(
                timestamp=now,
                severity="INFO",
                section=txt("ui.sync_report.section_operacion"),
                entity=txt("ui.sync_report.entity_sync"),
                message=details or txt("ui.sync_report.sin_detalle_adicional"),
            ),
        ],
        duration_ms=duracion_ms_entre_isos(start, now),
        error_count=1,
        success_rate=0.0,
        attempt_history=attempt_history
        or (SyncAttemptReport(attempt_number=1, status="ERROR", errors=1),),
    )


def build_simulation_report(
    plan: SyncExecutionPlan,
    *,
    source: str,
    scope: str,
    actor: str,
    sync_id: str | None = None,
    attempt_history: tuple[SyncAttemptReport, ...] = (),
    datetime_provider: type[datetime] = datetime,
) -> SyncReport:
    now, duration_ms = timestamp_y_duracion_simulacion(
        plan.generated_at,
        datetime_provider=datetime_provider,
    )
    entries = build_simulation_entries(plan, now)
    status = "OK" if plan.has_changes else "IDLE"
    return SyncReport(
        sync_id=sync_id or str(uuid.uuid4()),
        started_at=plan.generated_at,
        finished_at=now,
        attempts=max(1, len(attempt_history) or 1),
        final_status=status,
        status=status,
        source=source,
        scope=scope,
        idempotency_criteria=txt("ui.sync_report.idempotency_simulacion"),
        actor=actor,
        counts={
            "created": len(plan.to_create),
            "updated": len(plan.to_update),
            "skipped": len(plan.unchanged),
            "conflicts": len(plan.conflicts),
            "errors": len(plan.potential_errors),
        },
        warnings=[txt("ui.sync_report.simulacion_sin_escritura")],
        conflicts=[item.reason for item in plan.conflicts],
        errors=list(plan.potential_errors),
        entries=entries,
        duration_ms=duration_ms,
        rows_scanned_remote=len(plan.values_matrix),
        retry_count=max(0, len(attempt_history) - 1),
        conflicts_count=len(plan.conflicts),
        error_count=len(plan.potential_errors),
        success_rate=1.0 if not plan.potential_errors else 0.5,
        attempt_history=attempt_history
        or (
            SyncAttemptReport(
                attempt_number=1,
                status=status,
                created=len(plan.to_create),
                updated=len(plan.to_update),
                conflicts=len(plan.conflicts),
                errors=len(plan.potential_errors),
            ),
        ),
    )


