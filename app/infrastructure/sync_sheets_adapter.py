from __future__ import annotations

from collections.abc import Callable
import sqlite3

from app.domain.ports import (
    SheetsClientPort,
    SheetsConfigStorePort,
    SheetsRepositoryPort,
    SheetsSyncPort,
)
from app.domain.sync_models import SyncSummary
from app.application.use_cases.sync_sheets import SheetsSyncService


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
        return self._run_with_connection(lambda service: service.pull())

    def push(self) -> SyncSummary:
        return self._run_with_connection(lambda service: service.push())

    def sync(self) -> SyncSummary:
        return self._run_with_connection(lambda service: service.sync())

    def get_last_sync_at(self) -> str | None:
        return self._run_with_connection(lambda service: service.get_last_sync_at())

    def is_configured(self) -> bool:
        return self._run_with_connection(lambda service: service.is_configured())

    def store_sync_config_value(self, key: str, value: str) -> None:
        self._run_with_connection(lambda service: service.store_sync_config_value(key, value))

    def register_pdf_log(self, persona_id: int, fechas: list[str], pdf_hash: str | None) -> None:
        self._run_with_connection(lambda service: service.register_pdf_log(persona_id, fechas, pdf_hash))

    def _run_with_connection(self, operation):
        connection = self._connection_factory()
        try:
            service = SheetsSyncService(
                connection,
                self._config_store,
                self._client,
                self._repository,
            )
            return operation(service)
        finally:
            connection.close()
