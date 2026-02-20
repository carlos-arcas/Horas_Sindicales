from __future__ import annotations

import json
from dataclasses import replace
from datetime import datetime
from pathlib import Path

from app.domain.sync_models import SyncExecutionPlan, SyncLogEntry, SyncReport, SyncSummary


def build_sync_report(
    summary: SyncSummary,
    *,
    status: str,
    source: str,
    scope: str,
    actor: str,
    details: str | None = None,
    started_at: str | None = None,
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
    return SyncReport(
        started_at=started,
        finished_at=finished,
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
    )


def build_config_incomplete_report(source: str, scope: str, actor: str) -> SyncReport:
    report = SyncReport.empty()
    now = datetime.now().isoformat()
    return replace(
        report,
        started_at=now,
        finished_at=now,
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
    )


def build_failed_report(
    error_message: str,
    *,
    source: str,
    scope: str,
    actor: str,
    details: str | None,
    started_at: str | None,
) -> SyncReport:
    start = started_at or datetime.now().isoformat()
    now = datetime.now().isoformat()
    return SyncReport(
        started_at=start,
        finished_at=now,
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
    )



def build_simulation_report(
    plan: SyncExecutionPlan,
    *,
    source: str,
    scope: str,
    actor: str,
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
        started_at=plan.generated_at,
        finished_at=now,
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
    history_json = history_dir / f"sync_{stamp}.json"
    history_md = history_dir / f"sync_{stamp}.md"
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
    files = sorted(history_dir.glob("sync_*"), key=lambda item: item.stat().st_mtime, reverse=True)
    for old in files[max_entries * 2 :]:
        old.unlink(missing_ok=True)


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
