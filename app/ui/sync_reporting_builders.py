from __future__ import annotations

from app.domain.sync_models import SyncExecutionPlan, SyncLogEntry, SyncSummary
from app.ui.sync_reporting_formatters import txt


def build_warnings(summary: SyncSummary) -> list[str]:
    warnings: list[str] = []
    if summary.duplicates_skipped > 0:
        warnings.append(
            txt(
                "ui.sync_report.warning_solicitudes_existian",
                cantidad=summary.duplicates_skipped,
            )
        )
    if summary.omitted_by_delegada > 0:
        warnings.append(
            txt(
                "ui.sync_report.warning_filas_omitidas_delegada",
                cantidad=summary.omitted_by_delegada,
            )
        )
    return warnings


def build_errors(summary: SyncSummary) -> list[str]:
    if summary.errors <= 0:
        return []
    return [
        txt(
            "ui.sync_report.error_solicitudes_sincronizacion",
            cantidad=summary.errors,
        )
    ]


def build_conflicts(summary: SyncSummary) -> list[str]:
    if summary.conflicts_detected <= 0:
        return []
    return [
        txt(
            "ui.sync_report.conflictos_detectados",
            cantidad=summary.conflicts_detected,
        )
    ]


def calcular_tasa_exito(total_operations: int, errors: int) -> float:
    if total_operations == 0:
        return 1.0
    return max(0.0, (total_operations - errors) / total_operations)


def build_simulation_entries(plan: SyncExecutionPlan, now: str) -> list[SyncLogEntry]:
    entries: list[SyncLogEntry] = []
    for item in plan.to_create:
        entries.append(
            SyncLogEntry(
                timestamp=now,
                severity="INFO",
                section=txt("ui.sync_report.section_creaciones"),
                entity=txt("ui.sync_report.entity_solicitud"),
                message=txt("ui.sync_report.solicitud_nueva", uuid=item.uuid),
            )
        )
    for item in plan.to_update:
        entries.append(
            SyncLogEntry(
                timestamp=now,
                severity="INFO",
                section=txt("ui.sync_report.section_actualizaciones"),
                entity=txt("ui.sync_report.entity_solicitud"),
                message=txt(
                    "ui.sync_report.solicitud_cambios",
                    uuid=item.uuid,
                    cantidad=len(item.diffs),
                ),
            )
        )
        for diff in item.diffs:
            entries.append(
                SyncLogEntry(
                    timestamp=now,
                    severity="INFO",
                    section=txt("ui.sync_report.section_diff"),
                    entity=txt("ui.sync_report.entity_solicitud"),
                    message=txt(
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
                section=txt("ui.sync_report.section_conflictos"),
                entity=txt("ui.sync_report.entity_solicitud"),
                message=f"{item.uuid}: {item.reason}",
                suggested_action=txt("ui.sync_report.sugerencia_revisar_conflicto"),
            )
        )
    for error in plan.potential_errors:
        entries.append(
            SyncLogEntry(
                timestamp=now,
                severity="WARN",
                section=txt("ui.sync_report.section_validaciones"),
                entity=txt("ui.sync_report.entity_sync_planner"),
                message=error,
                suggested_action=txt("ui.sync_report.sugerencia_corregir_dato"),
            )
        )
    if entries:
        return entries
    return [
        SyncLogEntry(
            timestamp=now,
            severity="INFO",
            section=txt("ui.sync_report.section_operacion"),
            entity=txt("ui.sync_report.entity_sync_planner"),
            message=txt("ui.sync_report.no_hay_cambios"),
        )
    ]
