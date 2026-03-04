from __future__ import annotations

import logging
from datetime import UTC, datetime

from app.domain.sync_models import SyncLogEntry, SyncReport
from app.ui.copy_catalog import copy_text
from app.ui.tiempo.parseo_iso_datetime import (
    duracion_ms_desde_iso,
    normalizar_zona_horaria,
    parsear_iso_datetime,
)


logger = logging.getLogger(__name__)


def txt(key: str, **kwargs: object) -> str:
    template = copy_text(key)
    return template.format(**kwargs) if kwargs else template


def parsear_iso_utc_aware(valor_iso: str) -> datetime:
    dt = parsear_iso_datetime(valor_iso)
    return normalizar_zona_horaria(dt, UTC)


def duracion_ms_entre_isos(inicio_iso: str, fin_iso: str) -> int:
    return duracion_ms_desde_iso(inicio_iso, fin_iso, tz_objetivo=UTC)


def timestamp_y_duracion_simulacion(
    generated_at: str,
    *,
    datetime_provider: type[datetime] = datetime,
) -> tuple[str, int]:
    now_dt = datetime_provider.now()
    now = now_dt.isoformat()
    try:
        generated_at_dt = datetime_provider.fromisoformat(generated_at)
    except (TypeError, ValueError):
        logger.warning(
            "sync_simulacion_iso_invalido",
            extra={
                "evento": "sync_simulacion_iso_invalido",
                "generated_at": generated_at,
                "now": now,
            },
        )
        return now, 0

    if generated_at_dt.tzinfo is not None:
        now_dt = datetime_provider.now(generated_at_dt.tzinfo)
        now = now_dt.isoformat()
    elif now_dt.tzinfo is not None:
        now_dt = now_dt.replace(tzinfo=None)
        now = now_dt.isoformat()

    duration_ms = max(0, int((now_dt - generated_at_dt).total_seconds() * 1000))
    return now, duration_ms


def to_markdown(report: SyncReport) -> str:
    lines = [
        txt("ui.sync_report.md_titulo_informe"),
        txt("ui.sync_report.md_estado", estado=report.status),
        txt("ui.sync_report.md_inicio", inicio=report.started_at),
        txt("ui.sync_report.md_fin", fin=report.finished_at),
        txt("ui.sync_report.md_duracion", duracion_ms=report.duration_ms),
        txt("ui.sync_report.md_actor", actor=report.actor),
        txt("ui.sync_report.md_fuente", fuente=report.source),
        txt("ui.sync_report.md_alcance", alcance=report.scope),
        txt("ui.sync_report.md_idempotencia", idempotencia=report.idempotency_criteria),
        "",
        txt("ui.sync_report.seccion_resumen"),
        txt("ui.sync_report.md_solicitudes_creadas", cantidad=report.counts.get("created", 0)),
        txt(
            "ui.sync_report.md_solicitudes_actualizadas",
            cantidad=report.counts.get("updated", 0),
        ),
        txt("ui.sync_report.md_solicitudes_omitidas", cantidad=report.counts.get("skipped", 0)),
        txt(
            "ui.sync_report.md_conflictos_detectados",
            cantidad=report.counts.get("conflicts", 0),
        ),
        txt("ui.sync_report.md_errores", cantidad=report.counts.get("errors", 0)),
        txt("ui.sync_report.md_solicitudes_locales_totales", cantidad=report.rows_total_local),
        txt(
            "ui.sync_report.md_solicitudes_remotas_revisadas",
            cantidad=report.rows_scanned_remote,
        ),
        txt("ui.sync_report.md_llamadas_api", cantidad=report.api_calls_count),
        txt("ui.sync_report.md_reintentos", cantidad=report.retry_count),
        txt("ui.sync_report.md_conflictos_metrica", cantidad=report.conflicts_count),
        txt("ui.sync_report.md_errores_metrica", cantidad=report.error_count),
        txt("ui.sync_report.md_tasa_exito", tasa=report.success_rate),
        "",
        txt("ui.sync_report.seccion_detalle"),
    ]
    for entry in report.entries:
        lines.append(
            txt(
                "ui.sync_report.md_detalle_entry",
                timestamp=entry.timestamp,
                severity=entry.severity,
                section=entry.section,
                entity=entry.entity,
                message=entry.message,
            )
            + (
                txt("ui.sync_report.md_detalle_accion", accion=entry.suggested_action)
                if entry.suggested_action
                else ""
            )
        )
    return "\n".join(lines)


def build_base_entries(
    *,
    inserted_local: int,
    updated_local: int,
    inserted_remote: int,
    updated_remote: int,
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
            section=txt("ui.sync_report.section_operacion"),
            entity=txt("ui.sync_report.entity_sync"),
            message=txt("ui.sync_report.sincronizacion_finalizada"),
        ),
        SyncLogEntry(
            timestamp=finished,
            severity="INFO",
            section=txt("ui.sync_report.section_cambios_aplicados"),
            entity=txt("ui.sync_report.entity_solicitud"),
            message=txt(
                "ui.sync_report.cambios_aplicados_resumen",
                inserted_local=inserted_local,
                updated_local=updated_local,
                inserted_remote=inserted_remote,
                updated_remote=updated_remote,
            ),
        ),
    ]
    entries.extend(
        SyncLogEntry(
            timestamp=finished,
            severity="WARN",
            section=txt("ui.sync_report.section_cambios_aplicados"),
            entity=txt("ui.sync_report.entity_solicitud"),
            message=warning,
            suggested_action=txt("ui.sync_report.sugerencia_revisar_filtros"),
        )
        for warning in warnings
    )
    entries.extend(
        SyncLogEntry(
            timestamp=finished,
            severity="WARN",
            section=txt("ui.sync_report.section_conflictos"),
            entity=txt("ui.sync_report.entity_solicitud"),
            message=conflict,
            suggested_action=txt("ui.sync_report.sugerencia_abrir_solicitudes"),
        )
        for conflict in conflicts
    )
    entries.extend(
        SyncLogEntry(
            timestamp=finished,
            severity="ERROR",
            section=txt("ui.sync_report.section_errores"),
            entity=txt("ui.sync_report.entity_sync"),
            message=error,
            suggested_action=txt("ui.sync_report.sugerencia_reintentar_fallidos"),
        )
        for error in errors
    )
    if details:
        entries.append(
            SyncLogEntry(
                timestamp=finished,
                severity="INFO",
                section=txt("ui.sync_report.section_operacion"),
                entity=txt("ui.sync_report.entity_red"),
                message=details,
            )
        )
    return entries
