from __future__ import annotations

from pathlib import Path

from app.domain.models import SheetsConfig
from app.domain.ports import SheetsGatewayPort
from app.infrastructure.sheets_client import SheetsClient
from app.infrastructure.sheets_repository import SheetsRepository


class SheetsGatewayGspread(SheetsGatewayPort):
    def __init__(self, client: SheetsClient, repository: SheetsRepository) -> None:
        self._client = client
        self._repository = repository

    def test_connection(self, config: SheetsConfig, schema: dict[str, list[str]]) -> tuple[str, str, list[str]]:
        spreadsheet = self._client.open_spreadsheet(Path(config.credentials_path), config.spreadsheet_id)
        actions = self._repository.ensure_schema(spreadsheet, schema)
        return spreadsheet.title, spreadsheet.id, actions
