from __future__ import annotations

import json
import logging
import uuid
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

from app.domain.sync_models import SyncAttemptReport, SyncExecutionPlan, SyncLogEntry, SyncReport, SyncSummary
from app.ui.copy_catalog import copy_text

logger = logging.getLogger(__name__)


def _txt(key: str, **kwargs: object) -> str:
    template = copy_text(key)
    return template.format(**kwargs) if kwargs else template


def _parsear_iso_utc_aware(valor_iso: str) -> datetime:
    dt = datetime.fromisoformat(valor_iso)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _parse_iso_to_utc_aware(value: str) -> datetime:
    """Compat alias for existing callsites/tests."""
    return _parsear_iso_utc_aware(value)


def _duracion_ms_entre_isos(inicio_iso: str, fin_iso: str) -> int:
    inicio = _parsear_iso_utc_aware(inicio_iso)
    fin = _parsear_iso_utc_aware(fin_iso)
    return max(0, int((fin - inicio).total_seconds() * 1000))


def duracion_ms_desde_iso(inicio_iso: str, fin_iso: str) -> int:
    try:
        return _duracion_ms_entre_isos(inicio_iso, fin_iso)
    except (TypeError, ValueError):
        logger.warning(
            "No se pudo calcular duración desde ISO; se aplica fallback a 0 ms",
            extra={"inicio_iso": inicio_iso, "fin_iso": fin_iso},
        )
        return 0


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
    warnings: list[str] = []
    if summary.duplicates_skipped > 0:
        warnings.append(_txt("ui.sync_report.warning_solicitudes_existian", cantidad=summary.duplicates_skipped))
    if summary.omitted_by_delegada > 0:
        warnings.append(_txt("ui.sync_report.warning_filas_omitidas_delegada", cantidad=summary.omitted_by_delegada))

    errors = []
    if summary.errors > 0:
        errors.append(_txt("ui.sync_report.error_solicitudes_sincronizacion", cantidad=summary.errors))

    conflicts = []
    if summary.conflicts_detected > 0:
        conflicts.append(_txt("ui.sync_report.conflictos_detectados", cantidad=summary.conflicts_detected))

    entries = _base_entries(summary, warnings=warnings, errors=errors, conflicts=conflicts, details=details, finished=finished)
    duration_ms = _duracion_ms_entre_isos(started, finished)
    attempts = max(1, len(attempt_history) or 1)
    total_operations = summary.inserted_local + summary.updated_local + summary.inserted_remote + summary.updated_remote
    success_rate = 1.0 if total_operations == 0 else max(0.0, (total_operations - summary.errors) / total_operations)

    return SyncReport(
        sync_id=sync_id or str(uuid.uuid4()),
        started_at=started,
        finished_at=finished,
        attempts=attempts,
        final_status=status,
        status=status,
        source=source,
        scope=scope,
        idempotency_criteria=_txt("ui.sync_report.idempotency_criteria"),
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
            _txt("ui.sync_report.items_changed_local", created=summary.inserted_local, updated=summary.updated_local),
            _txt("ui.sync_report.items_changed_sheets", created=summary.inserted_remote, updated=summary.updated_remote),
        ],
        entries=entries,
        duration_ms=duration_ms,
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
                section=_txt("ui.sync_report.section_operacion"),
                entity=_txt("ui.sync_report.entity_config"),
                message=_txt("ui.sync_report.error_falta_config"),
                suggested_action=_txt("ui.sync_report.sugerencia_ir_config"),
            )
        ],
        errors=[_txt("ui.sync_report.error_config_incompleta")],
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
        idempotency_criteria=_txt("ui.sync_report.idempotency_criteria"),
        actor=actor,
        counts={"created": 0, "updated": 0, "skipped": 0, "conflicts": 0, "errors": 1},
        errors=[error_message],
        entries=[
            SyncLogEntry(
                timestamp=now,
                severity="ERROR",
                section=_txt("ui.sync_report.section_errores"),
                entity=_txt("ui.sync_report.entity_red"),
                message=error_message,
                suggested_action=_txt("ui.sync_report.sugerencia_revisar_config_red"),
            ),
            SyncLogEntry(
                timestamp=now,
                severity="INFO",
                section=_txt("ui.sync_report.section_operacion"),
                entity=_txt("ui.sync_report.entity_sync"),
                message=details or _txt("ui.sync_report.sin_detalle_adicional"),
            ),
        ],
        duration_ms=_duracion_ms_entre_isos(start, now),
        error_count=1,
        success_rate=0.0,
        attempt_history=attempt_history or (SyncAttemptReport(attempt_number=1, status="ERROR", errors=1),),
    )



def build_simulation_report(
    plan: SyncExecutionPlan,
    *,
    source: str,
    scope: str,
    actor: str,
    sync_id: str | None = None,
    attempt_history: tuple[SyncAttemptReport, ...] = (),
) -> SyncReport:
    now = datetime.now().isoformat()
    entries: list[SyncLogEntry] = []
    for item in plan.to_create:
        entries.append(
            SyncLogEntry(
                timestamp=now,
                severity="INFO",
                section=_txt("ui.sync_report.section_creaciones"),
                entity=_txt("ui.sync_report.entity_solicitud"),
                message=_txt("ui.sync_report.solicitud_nueva", uuid=item.uuid),
            )
        )
    for item in plan.to_update:
        entries.append(
            SyncLogEntry(
                timestamp=now,
                severity="INFO",
                section=_txt("ui.sync_report.section_actualizaciones"),
                entity=_txt("ui.sync_report.entity_solicitud"),
                message=_txt("ui.sync_report.solicitud_cambios", uuid=item.uuid, cantidad=len(item.diffs)),
            )
        )
        for diff in item.diffs:
            entries.append(
                SyncLogEntry(
                    timestamp=now,
                    severity="INFO",
                    section=_txt("ui.sync_report.section_diff"),
                    entity=_txt("ui.sync_report.entity_solicitud"),
                    message=_txt(
                        "ui.sync_report.diff_line",
                        uuid=item.uuid,
                        field=diff.field,
                        current_value=diff.current_value,
                        new_value=diff.new_value,
                    ),
                )
            )
    for item in plan.conflicts:
        entries.append(
            SyncLogEntry(
                timestamp=now,
                severity="WARN",
                section=_txt("ui.sync_report.section_conflictos"),
                entity=_txt("ui.sync_report.entity_solicitud"),
                message=f"{item.uuid}: {item.reason}",
                suggested_action=_txt("ui.sync_report.sugerencia_revisar_conflicto"),
            )
        )
    for error in plan.potential_errors:
        entries.append(
            SyncLogEntry(
                timestamp=now,
                severity="WARN",
                section=_txt("ui.sync_report.section_validaciones"),
                entity=_txt("ui.sync_report.entity_sync_planner"),
                message=error,
                suggested_action=_txt("ui.sync_report.sugerencia_corregir_dato"),
            )
        )
    if not entries:
        entries.append(
            SyncLogEntry(
                timestamp=now,
                severity="INFO",
                section=_txt("ui.sync_report.section_operacion"),
                entity=_txt("ui.sync_report.entity_sync_planner"),
                message=_txt("ui.sync_report.no_hay_cambios"),
            )
        )
    status = "OK" if plan.has_changes else "IDLE"
    duration_ms = duracion_ms_desde_iso(plan.generated_at, now)

    return SyncReport(
        sync_id=sync_id or str(uuid.uuid4()),
        started_at=plan.generated_at,
        finished_at=now,
        attempts=max(1, len(attempt_history) or 1),
        final_status=status,
        status=status,
        source=source,
        scope=scope,
        idempotency_criteria=_txt("ui.sync_report.idempotency_simulacion"),
        actor=actor,
        counts={
            "created": len(plan.to_create),
            "updated": len(plan.to_update),
            "skipped": len(plan.unchanged),
            "conflicts": len(plan.conflicts),
            "errors": len(plan.potential_errors),
        },
        warnings=[_txt("ui.sync_report.simulacion_sin_escritura")],
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

def persist_report(report: SyncReport, root: Path) -> tuple[Path, Path]:
    logs_dir = root / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    json_path = logs_dir / "sync_last.json"
    md_path = logs_dir / "sync_last.md"
    json_path.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(to_markdown(report), encoding="utf-8")

    history_dir = logs_dir / "sync_history"
    history_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime(_txt("ui.sync_report.timestamp_format"))
    sync_id = report.sync_id or "no-sync-id"
    history_json = history_dir / f"{stamp}_{sync_id}.json"
    history_md = history_dir / f"{stamp}_{sync_id}.md"
    history_json.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    history_md.write_text(to_markdown(report), encoding="utf-8")
    _trim_history(history_dir)
    return json_path, md_path


def to_markdown(report: SyncReport) -> str:
    lines = [
        _txt("ui.sync_report.md_titulo_informe"),
        _txt("ui.sync_report.md_estado", estado=report.status),
        _txt("ui.sync_report.md_inicio", inicio=report.started_at),
        _txt("ui.sync_report.md_fin", fin=report.finished_at),
        _txt("ui.sync_report.md_duracion", duracion_ms=report.duration_ms),
        _txt("ui.sync_report.md_actor", actor=report.actor),
        _txt("ui.sync_report.md_fuente", fuente=report.source),
        _txt("ui.sync_report.md_alcance", alcance=report.scope),
        _txt("ui.sync_report.md_idempotencia", idempotencia=report.idempotency_criteria),
        "",
        _txt("ui.sync_report.seccion_resumen"),
        _txt("ui.sync_report.md_solicitudes_creadas", cantidad=report.counts.get("created", 0)),
        _txt("ui.sync_report.md_solicitudes_actualizadas", cantidad=report.counts.get("updated", 0)),
        _txt("ui.sync_report.md_solicitudes_omitidas", cantidad=report.counts.get("skipped", 0)),
        _txt("ui.sync_report.md_conflictos_detectados", cantidad=report.counts.get("conflicts", 0)),
        _txt("ui.sync_report.md_errores", cantidad=report.counts.get("errors", 0)),
        _txt("ui.sync_report.md_solicitudes_locales_totales", cantidad=report.rows_total_local),
        _txt("ui.sync_report.md_solicitudes_remotas_revisadas", cantidad=report.rows_scanned_remote),
        _txt("ui.sync_report.md_llamadas_api", cantidad=report.api_calls_count),
        _txt("ui.sync_report.md_reintentos", cantidad=report.retry_count),
        _txt("ui.sync_report.md_conflictos_metrica", cantidad=report.conflicts_count),
        _txt("ui.sync_report.md_errores_metrica", cantidad=report.error_count),
        _txt("ui.sync_report.md_tasa_exito", tasa=report.success_rate),
        "",
        _txt("ui.sync_report.seccion_detalle"),
    ]
    for entry in report.entries:
        lines.append(
            _txt(
                "ui.sync_report.md_detalle_entry",
                timestamp=entry.timestamp,
                severity=entry.severity,
                section=entry.section,
                entity=entry.entity,
                message=entry.message,
            )
            + (
                _txt("ui.sync_report.md_detalle_accion", accion=entry.suggested_action)
                if entry.suggested_action
                else ""
            )
        )
    return "\n".join(lines)


def _trim_history(history_dir: Path, max_entries: int = 20) -> None:
    files = sorted(history_dir.glob(_txt("ui.sync_report.glob_json")), key=lambda item: item.stat().st_mtime, reverse=True)
    companion_md = {path.with_suffix(".md") for path in files}
    all_files = files + [path for path in companion_md if path.exists()]
    for old in all_files[max_entries * 2 :]:
        old.unlink(missing_ok=True)


def list_sync_history(root: Path) -> list[Path]:
    history_dir = root / "logs" / "sync_history"
    if not history_dir.exists():
        return []
    return sorted(history_dir.glob(_txt("ui.sync_report.glob_json")), key=lambda item: item.stat().st_mtime, reverse=True)


def load_sync_report(path: Path) -> SyncReport:
    data = json.loads(path.read_text(encoding="utf-8"))
    entries = [SyncLogEntry(**entry) for entry in data.get("entries", [])]
    attempts = [SyncAttemptReport(**attempt) for attempt in data.get("attempt_history", [])]
    return SyncReport(
        sync_id=data.get("sync_id", ""),
        started_at=data["started_at"],
        finished_at=data["finished_at"],
        attempts=int(data.get("attempts", 1)),
        final_status=data.get("final_status", data.get("status", "IDLE")),
        status=data.get("status", "IDLE"),
        source=data.get("source", ""),
        scope=data.get("scope", ""),
        idempotency_criteria=data.get("idempotency_criteria", ""),
        actor=data.get("actor", _txt("ui.sync_report.no_disponible_abrev")),
        counts=data.get("counts", {}),
        warnings=data.get("warnings", []),
        errors=data.get("errors", []),
        conflicts=data.get("conflicts", []),
        items_changed=data.get("items_changed", []),
        entries=entries,
        duration_ms=int(data.get("duration_ms", 0)),
        rows_total_local=int(data.get("rows_total_local", 0)),
        rows_scanned_remote=int(data.get("rows_scanned_remote", 0)),
        api_calls_count=int(data.get("api_calls_count", 0)),
        retry_count=int(data.get("retry_count", 0)),
        conflicts_count=int(data.get("conflicts_count", 0)),
        error_count=int(data.get("error_count", 0)),
        success_rate=float(data.get("success_rate", 1.0)),
        attempt_history=tuple(attempts),
    )


def _base_entries(
    summary: SyncSummary,
    *,
    warnings: list[str],
    errors: list[str],
    conflicts: list[str],
    details: str | None,
    finished: str,
) -> list[SyncLogEntry]:
    entries = [
        SyncLogEntry(
            timestamp=finished,
            severity="INFO",
            section=_txt("ui.sync_report.section_operacion"),
            entity=_txt("ui.sync_report.entity_sync"),
            message=_txt("ui.sync_report.sincronizacion_finalizada"),
        ),
        SyncLogEntry(
            timestamp=finished,
            severity="INFO",
            section=_txt("ui.sync_report.section_cambios_aplicados"),
            entity=_txt("ui.sync_report.entity_solicitud"),
            message=_txt(
                "ui.sync_report.cambios_aplicados_resumen",
                inserted_local=summary.inserted_local,
                updated_local=summary.updated_local,
                inserted_remote=summary.inserted_remote,
                updated_remote=summary.updated_remote,
            ),
        ),
    ]
    entries.extend(
        SyncLogEntry(
            timestamp=finished,
            severity="WARN",
            section=_txt("ui.sync_report.section_cambios_aplicados"),
            entity=_txt("ui.sync_report.entity_solicitud"),
            message=warning,
            suggested_action=_txt("ui.sync_report.sugerencia_revisar_filtros"),
        )
        for warning in warnings
    )
    entries.extend(
        SyncLogEntry(
            timestamp=finished,
            severity="WARN",
            section=_txt("ui.sync_report.section_conflictos"),
            entity=_txt("ui.sync_report.entity_solicitud"),
            message=conflict,
            suggested_action=_txt("ui.sync_report.sugerencia_abrir_solicitudes"),
        )
        for conflict in conflicts
    )
    entries.extend(
        SyncLogEntry(
            timestamp=finished,
            severity="ERROR",
            section=_txt("ui.sync_report.section_errores"),
            entity=_txt("ui.sync_report.entity_sync"),
            message=error,
            suggested_action=_txt("ui.sync_report.sugerencia_reintentar_fallidos"),
        )
        for error in errors
    )
    if details:
        entries.append(
            SyncLogEntry(
                timestamp=finished,
                severity="INFO",
                section=_txt("ui.sync_report.section_operacion"),
                entity=_txt("ui.sync_report.entity_red"),
                message=details,
            )
        )
    return entries
