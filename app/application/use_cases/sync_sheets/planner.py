from __future__ import annotations

from typing import Any

from app.domain.sync_models import SyncExecutionPlan


def build_plan(service: Any, spreadsheet: Any) -> SyncExecutionPlan:
    """Construye el SyncExecutionPlan reutilizando la implementación actual del servicio."""
    return service._build_solicitudes_sync_plan(spreadsheet)
