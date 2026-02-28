from __future__ import annotations

from app.domain.ports import SheetsSyncPort
from app.domain.sync_models import SyncExecutionPlan, SyncSummary
from app.core.metrics import medir_tiempo, metrics_registry


class SyncSheetsUseCase:
    """Fachada de aplicación para sincronización bidireccional con Sheets.

    Mantiene el contrato de la UI desacoplado de la infraestructura concreta y
    facilita sustituir la estrategia de sync sin tocar consumidores.
    """
    def __init__(self, sync_port: SheetsSyncPort) -> None:
        self._sync_port = sync_port

    def pull(self) -> SyncSummary:
        return self._sync_port.pull()

    def push(self) -> SyncSummary:
        return self._sync_port.push()

    def sync(self) -> SyncSummary:
        return self.sync_bidirectional()

    @medir_tiempo("latency.sync_bidireccional_ms")
    def sync_bidirectional(self) -> SyncSummary:
        metrics_registry.incrementar("syncs_ejecutados")
        summary = self._sync_port.sync_bidirectional()
        if summary.conflicts_detected > 0:
            metrics_registry.incrementar("conflictos_detectados", summary.conflicts_detected)
        return summary

    def simulate_sync_plan(self) -> SyncExecutionPlan:
        return self._sync_port.simulate_sync_plan()

    def execute_sync_plan(self, plan: SyncExecutionPlan) -> SyncSummary:
        return self._sync_port.execute_sync_plan(plan)

    def is_configured(self) -> bool:
        return self._sync_port.is_configured()

    def get_last_sync_at(self) -> str | None:
        return self._sync_port.get_last_sync_at()

    def register_pdf_log(self, persona_id: int, fechas: list[str], pdf_hash: str | None) -> None:
        self._sync_port.register_pdf_log(persona_id, fechas, pdf_hash)

    def store_sync_config_value(self, key: str, value: str) -> None:
        self._sync_port.store_sync_config_value(key, value)

    def ensure_connection(self) -> None:
        self._sync_port.ensure_connection()
