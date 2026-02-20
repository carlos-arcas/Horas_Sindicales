from __future__ import annotations

import json
import uuid
from dataclasses import replace
from datetime import datetime
from pathlib import Path

from app.domain.sync_models import SyncAttemptReport, SyncExecutionPlan, SyncLogEntry, SyncReport, SyncSummary


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
        warnings.append(f"{summary.duplicates_skipped} filas omitidas por idempotencia (sin cambios).")
    if summary.omitted_by_delegada > 0:
        warnings.append(f"{summary.omitted_by_delegada} filas omitidas por filtro de delegada.")

    errors = []
    if summary.errors > 0:
        errors.append(f"Se detectaron {summary.errors} errores durante la sincronización.")

    conflicts = []
    if summary.conflicts_detected > 0:
        conflicts.append(f"Se detectaron {summary.conflicts_detected} conflictos.")

    entries = _base_entries(summary, warnings=warnings, errors=errors, conflicts=conflicts, details=details, finished=finished)
    started_dt = datetime.fromisoformat(started)
    finished_dt = datetime.fromisoformat(finished)
    duration_ms = max(0, int((finished_dt - started_dt).total_seconds() * 1000))
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
        idempotency_criteria="Clave única solicitud: delegada_uuid + fecha + tramo horario/completo.",
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
            f"Local: +{summary.inserted_local} / ~{summary.updated_local}",
            f"Sheets: +{summary.inserted_remote} / ~{summary.updated_remote}",
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
                section="Operación",
                entity="Config",
                message="Falta configuración de Google Sheets (Spreadsheet ID o credenciales).",
                suggested_action="Ir a configuración y completar los campos obligatorios.",
            )
        ],
        errors=["Configuración incompleta."],
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
        idempotency_criteria="Clave única solicitud: delegada_uuid + fecha + tramo horario/completo.",
        actor=actor,
        counts={"created": 0, "updated": 0, "skipped": 0, "conflicts": 0, "errors": 1},
        errors=[error_message],
        entries=[
            SyncLogEntry(
                timestamp=now,
                severity="ERROR",
                section="Errores",
                entity="Red",
                message=error_message,
                suggested_action="Revisar configuración/conectividad y reintentar solo fallidos.",
            ),
            SyncLogEntry(
                timestamp=now,
                severity="INFO",
                section="Operación",
                entity="Sync",
                message=details or "Sin detalle adicional.",
            ),
        ],
        duration_ms=max(0, int((datetime.fromisoformat(now) - datetime.fromisoformat(start)).total_seconds() * 1000)),
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
                section="Creaciones",
                entity="Solicitud",
                message=f"{item.uuid}: Nuevo registro",
            )
        )
    for item in plan.to_update:
        entries.append(
            SyncLogEntry(
                timestamp=now,
                severity="INFO",
                section="Actualizaciones",
                entity="Solicitud",
                message=f"{item.uuid}: {len(item.diffs)} campo(s) con cambios.",
            )
        )
        for diff in item.diffs:
            entries.append(
                SyncLogEntry(
                    timestamp=now,
                    severity="INFO",
                    section="Diff",
                    entity="Solicitud",
                    message=f"{item.uuid} | {diff.field} | actual: {diff.current_value} | nuevo: {diff.new_value}",
                )
            )
    for item in plan.conflicts:
        entries.append(
            SyncLogEntry(
                timestamp=now,
                severity="WARN",
                section="Conflictos",
                entity="Solicitud",
                message=f"{item.uuid}: {item.reason}",
                suggested_action="Resolver conflicto antes de sincronizar.",
            )
        )
    for error in plan.potential_errors:
        entries.append(
            SyncLogEntry(
                timestamp=now,
                severity="WARN",
                section="Validaciones",
                entity="SyncPlanner",
                message=error,
                suggested_action="Corregir dato y volver a simular.",
            )
        )
    if not entries:
        entries.append(
            SyncLogEntry(
                timestamp=now,
                severity="INFO",
                section="Operación",
                entity="SyncPlanner",
                message="No hay cambios que aplicar.",
            )
        )
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
        idempotency_criteria="Plan inmutable generado por SyncPlanner antes de ejecutar SyncExecutor.",
        actor=actor,
        counts={
            "created": len(plan.to_create),
            "updated": len(plan.to_update),
            "skipped": len(plan.unchanged),
            "conflicts": len(plan.conflicts),
            "errors": len(plan.potential_errors),
        },
        warnings=["Simulación sin escritura en Google Sheets."],
        conflicts=[item.reason for item in plan.conflicts],
        errors=list(plan.potential_errors),
        entries=entries,
        duration_ms=max(0, int((datetime.fromisoformat(now) - datetime.fromisoformat(plan.generated_at)).total_seconds() * 1000)),
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
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    sync_id = report.sync_id or "no-sync-id"
    history_json = history_dir / f"{stamp}_{sync_id}.json"
    history_md = history_dir / f"{stamp}_{sync_id}.md"
    history_json.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    history_md.write_text(to_markdown(report), encoding="utf-8")
    _trim_history(history_dir)
    return json_path, md_path


def to_markdown(report: SyncReport) -> str:
    lines = [
        "# Informe de sincronización",
        f"- Estado: **{report.status}**",
        f"- Inicio: {report.started_at}",
        f"- Fin: {report.finished_at}",
        f"- Duración: {report.duration_ms} ms",
        f"- Actor: {report.actor}",
        f"- Fuente: {report.source}",
        f"- Alcance: {report.scope}",
        f"- Idempotencia: {report.idempotency_criteria}",
        "",
        "## Resumen",
        f"- Filas creadas: {report.counts.get('created', 0)}",
        f"- Filas actualizadas: {report.counts.get('updated', 0)}",
        f"- Filas omitidas (sin cambios): {report.counts.get('skipped', 0)}",
        f"- Conflictos detectados: {report.counts.get('conflicts', 0)}",
        f"- Errores: {report.counts.get('errors', 0)}",
        f"- Filas locales totales: {report.rows_total_local}",
        f"- Filas remotas escaneadas: {report.rows_scanned_remote}",
        f"- Llamadas API: {report.api_calls_count}",
        f"- Reintentos: {report.retry_count}",
        f"- Conflictos (métrica): {report.conflicts_count}",
        f"- Errores (métrica): {report.error_count}",
        f"- Tasa de éxito: {report.success_rate:.0%}",
        "",
        "## Detalle",
    ]
    for entry in report.entries:
        lines.append(
            f"- [{entry.timestamp}] **{entry.severity}** · {entry.section}/{entry.entity}: {entry.message}"
            + (f". Acción: {entry.suggested_action}" if entry.suggested_action else "")
        )
    return "\n".join(lines)


def _trim_history(history_dir: Path, max_entries: int = 20) -> None:
    files = sorted(history_dir.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True)
    companion_md = {path.with_suffix(".md") for path in files}
    all_files = files + [path for path in companion_md if path.exists()]
    for old in all_files[max_entries * 2 :]:
        old.unlink(missing_ok=True)


def list_sync_history(root: Path) -> list[Path]:
    history_dir = root / "logs" / "sync_history"
    if not history_dir.exists():
        return []
    return sorted(history_dir.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True)


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
        actor=data.get("actor", "N/D"),
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
            section="Operación",
            entity="Sync",
            message="Sincronización finalizada.",
        ),
        SyncLogEntry(
            timestamp=finished,
            severity="INFO",
            section="Cambios aplicados",
            entity="Solicitud",
            message=(
                f"Local +{summary.inserted_local}/~{summary.updated_local}; "
                f"Sheets +{summary.inserted_remote}/~{summary.updated_remote}."
            ),
        ),
    ]
    entries.extend(
        SyncLogEntry(
            timestamp=finished,
            severity="WARN",
            section="Cambios aplicados",
            entity="Solicitud",
            message=warning,
            suggested_action="Revisar filtros y confirmar si el comportamiento era esperado.",
        )
        for warning in warnings
    )
    entries.extend(
        SyncLogEntry(
            timestamp=finished,
            severity="WARN",
            section="Conflictos",
            entity="Solicitud",
            message=conflict,
            suggested_action="Abrir registros afectados y marcar para revisión.",
        )
        for conflict in conflicts
    )
    entries.extend(
        SyncLogEntry(
            timestamp=finished,
            severity="ERROR",
            section="Errores",
            entity="Sync",
            message=error,
            suggested_action="Reintentar solo fallidos.",
        )
        for error in errors
    )
    if details:
        entries.append(
            SyncLogEntry(
                timestamp=finished,
                severity="INFO",
                section="Operación",
                entity="Red",
                message=details,
            )
        )
    return entries
