from __future__ import annotations

from typing import Any

from app.application.use_cases.sync_sheets.executor import execute_plan
from app.application.use_cases.sync_sheets.orquestador_persistencia import OrquestadorPersistenciaSync
from app.application.use_cases.sync_sheets.orquestador_preflight import OrquestadorPreflightSync
from app.application.use_cases.sync_sheets.orquestador_pull import OrquestadorPullSheets
from app.application.use_cases.sync_sheets.orquestador_push import OrquestadorPushSheets
from app.application.use_cases.sync_sheets.orquestacion_modelos import (
    HEADER_CANONICO_SOLICITUDES,
    PullApplyContext,
)
from app.application.use_cases.sync_sheets.planner import build_plan
from app.application.use_cases.sync_sheets.servicio_escritura_lotes import ServicioEscrituraLotes
from app.application.use_cases.sync_sheets.pull_planner import PullPlannerSignals, plan_pull_actions
from app.application.use_cases.sync_sheets.pull_runner import run_pull_actions, run_with_savepoint
from app.application.use_cases import sync_sheets_core
from app.application.use_cases.sync_sheets.normalization_rules import normalize_remote_uuid
from app.application.delegada_resolution import get_or_resolve_delegada_uuid
from app.application.use_cases.sync_sheets.push_builder import build_push_solicitudes_payloads
from app.application.use_cases.sync_sheets.push_runner import run_push_values_update
from app.application.use_cases.sync_sheets.sync_reporting_rules import (
    apply_stat_counter,
    combine_sync_summaries,
    pull_stats_tuple,
    reason_text,
)
from app.application.use_cases.sync_sheets.sync_snapshots import (
    PullContext,
    PullSignals,
    RemoteSolicitudRowDTO,
    build_pull_signals_snapshot,
    parse_remote_solicitud_row,
)
from app.domain.ports import (
    SheetsClientPort,
    SheetsConfigStorePort,
    SheetsRepositoryPort,
    SqlConnectionPort,
)
from app.domain.sync_models import SyncExecutionPlan, SyncSummary

class SheetsSyncService(
    OrquestadorPreflightSync,
    OrquestadorPullSheets,
    OrquestadorPushSheets,
    OrquestadorPersistenciaSync,
):
    def __init__(
        self,
        connection: SqlConnectionPort,
        config_store: SheetsConfigStorePort,
        client: SheetsClientPort,
        repository: SheetsRepositoryPort,
        *,
        enable_backfill: bool = False,
    ) -> None:
        self._connection = connection
        self._config_store = config_store
        self._client = client
        self._repository = repository
        self._worksheet_cache: dict[str, Any] = {}
        self._servicio_escritura_lotes = ServicioEscrituraLotes()
        self._pending_append_rows = self._servicio_escritura_lotes.pendientes_altas
        self._pending_batch_updates = self._servicio_escritura_lotes.pendientes_actualizaciones
        self._pending_values_batch_updates = self._servicio_escritura_lotes.pendientes_backfill
        self._worksheet_next_append_row = self._servicio_escritura_lotes.siguiente_fila_append
        self._enable_backfill = enable_backfill
        self._defer_local_commits = False
        self._pull_apply_context: PullApplyContext | None = None
        self._delegadas_nombre_por_uuid_cache: dict[str, str] | None = None

    def pull(self) -> SyncSummary:
        spreadsheet = self._ensure_connection_ready()
        summary = self._pull_with_spreadsheet(spreadsheet)
        self._log_sync_stats("pull")
        return summary

    def push(self) -> SyncSummary:
        spreadsheet = self._ensure_connection_ready()
        preflight = self.preflight_permisos_escritura(spreadsheet)
        if not preflight.ok:
            return self._resolver_preflight_denegado(preflight)
        summary = self._push_with_spreadsheet(spreadsheet)
        self._log_sync_stats("push")
        return summary

    def sync(self) -> SyncSummary:
        return self.sync_bidirectional()

    def sync_bidirectional(self) -> SyncSummary:
        spreadsheet = self._ensure_connection_ready()
        pull_summary = self._pull_with_spreadsheet(spreadsheet)
        self._connection.commit()
        preflight = self.preflight_permisos_escritura(spreadsheet)
        if not preflight.ok:
            if self._strict_sync_exceptions_enabled():
                raise self._build_permission_error(preflight)
            self._registrar_issue_preflight(preflight)
            self._log_sync_stats("sync_bidirectional")
            return combine_sync_summaries(pull_summary, SyncSummary(errors=1))
        push_summary = self._push_with_spreadsheet(spreadsheet)
        self._log_sync_stats("sync_bidirectional")
        return combine_sync_summaries(pull_summary, push_summary)

    def simulate_sync_plan(self) -> SyncExecutionPlan:
        spreadsheet = self._ensure_connection_ready()
        return build_plan(self, spreadsheet)

    def execute_sync_plan(self, plan: SyncExecutionPlan) -> SyncSummary:
        spreadsheet = self._ensure_connection_ready()
        return execute_plan(self, spreadsheet, plan)

    def get_last_sync_at(self) -> str | None:
        return self._get_last_sync_at()

    def is_configured(self) -> bool:
        config = self._config_store.load()
        return bool(config and config.spreadsheet_id and config.credentials_path)

    def ensure_connection(self) -> None:
        self._ensure_connection_ready()

    def get_service_account_email(self) -> str | None:
        return self._client.get_service_account_email()


__all__ = [
    "HEADER_CANONICO_SOLICITUDES",
    "PullContext",
    "PullPlannerSignals",
    "PullSignals",
    "RemoteSolicitudRowDTO",
    "SheetsSyncService",
    "apply_stat_counter",
    "build_pull_signals_snapshot",
    "build_push_solicitudes_payloads",
    "get_or_resolve_delegada_uuid",
    "normalize_remote_uuid",
    "parse_remote_solicitud_row",
    "plan_pull_actions",
    "pull_stats_tuple",
    "reason_text",
    "run_pull_actions",
    "run_push_values_update",
    "run_with_savepoint",
    "sync_sheets_core",
]
