from __future__ import annotations

from datetime import datetime

from app.domain.sync_models import SyncAttemptReport, SyncExecutionPlan, SyncReport
from app.ui.sync_reporting_formatters import (
    duracion_ms_entre_isos,
    parsear_iso_utc_aware,
    to_markdown,
)
from app.ui.sync_reporting_orquestacion import (
    build_config_incomplete_report,
    build_failed_report,
    build_simulation_report as _build_simulation_report,
    build_sync_report,
)
from app.ui.sync_reporting_storage import list_sync_history, load_sync_report, persist_report


# Compat wrappers para callsites/tests existentes.
def _parsear_iso_utc_aware(valor_iso: str) -> datetime:
    return parsear_iso_utc_aware(valor_iso)


def _parse_iso_to_utc_aware(value: str) -> datetime:
    return _parsear_iso_utc_aware(value)


def _duracion_ms_entre_isos(inicio_iso: str, fin_iso: str) -> int:
    return duracion_ms_entre_isos(inicio_iso, fin_iso)


def build_simulation_report(
    plan: SyncExecutionPlan,
    *,
    source: str,
    scope: str,
    actor: str,
    sync_id: str | None = None,
    attempt_history: tuple[SyncAttemptReport, ...] = (),
) -> SyncReport:
    return _build_simulation_report(
        plan,
        source=source,
        scope=scope,
        actor=actor,
        sync_id=sync_id,
        attempt_history=attempt_history,
        datetime_provider=datetime,
    )


__all__ = [
    "build_config_incomplete_report",
    "build_failed_report",
    "build_simulation_report",
    "build_sync_report",
    "list_sync_history",
    "load_sync_report",
    "persist_report",
    "to_markdown",
    "_parsear_iso_utc_aware",
    "_parse_iso_to_utc_aware",
    "_duracion_ms_entre_isos",
]
