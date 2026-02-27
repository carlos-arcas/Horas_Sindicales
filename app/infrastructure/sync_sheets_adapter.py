from __future__ import annotations

from collections.abc import Callable
import sqlite3

from app.domain.ports import (
    SheetsClientPort,
    SheetsConfigStorePort,
    SheetsRepositoryPort,
    SheetsSyncPort,
)
from app.domain.sync_models import SyncExecutionPlan, SyncSummary
from app.application.use_cases.sync_sheets import SheetsSyncService
from app.infrastructure.sync_sheets_adapter_puros import (
    build_service_operation,
    ensure_execution_plan_shape,
    normalize_pdf_log_input,
    normalize_sync_config_input,
)


class SyncSheetsAdapter(SheetsSyncPort):
    def __init__(
        self,
        connection_factory: Callable[[], sqlite3.Connection],
        config_store: SheetsConfigStorePort,
        client: SheetsClientPort,
        repository: SheetsRepositoryPort,
    ) -> None:
        self._connection_factory = connection_factory
        self._config_store = config_store
        self._client = client
        self._repository = repository

    def pull(self) -> SyncSummary:
        return self._run_with_connection(build_service_operation("pull"))

    def push(self) -> SyncSummary:
        return self._run_with_connection(build_service_operation("push"))

    def sync(self) -> SyncSummary:
        return self.sync_bidirectional()

    def sync_bidirectional(self) -> SyncSummary:
        return self._run_with_connection(build_service_operation("sync_bidirectional"))

    def simulate_sync_plan(self) -> SyncExecutionPlan:
        return self._run_with_connection(build_service_operation("simulate_sync_plan"))

    def execute_sync_plan(self, plan: SyncExecutionPlan) -> SyncSummary:
        normalized_plan = ensure_execution_plan_shape(plan)
        return self._run_with_connection(build_service_operation("execute_sync_plan", normalized_plan))

    def get_last_sync_at(self) -> str | None:
        return self._run_with_connection(build_service_operation("get_last_sync_at"))

    def is_configured(self) -> bool:
        return self._run_with_connection(build_service_operation("is_configured"))

    def store_sync_config_value(self, key: str, value: str) -> None:
        normalized_key, normalized_value = normalize_sync_config_input(key, value)
        self._run_with_connection(build_service_operation("store_sync_config_value", normalized_key, normalized_value))

    def register_pdf_log(self, persona_id: int, fechas: list[str], pdf_hash: str | None) -> None:
        normalized = normalize_pdf_log_input(persona_id, fechas, pdf_hash)
        self._run_with_connection(build_service_operation("register_pdf_log", *normalized))

    def ensure_connection(self) -> None:
        self._run_with_connection(build_service_operation("ensure_connection"))

    def _run_with_connection(self, operation):
        connection = self._connection_factory()
        try:
            service = SheetsSyncService(connection, self._config_store, self._client, self._repository)
            return operation(service)
        finally:
            connection.close()
