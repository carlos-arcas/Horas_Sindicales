from __future__ import annotations

import logging
from pathlib import Path

import gspread

from app.domain.ports import SheetsClientPort
from app.infrastructure.sheets_errors import map_gspread_exception

logger = logging.getLogger(__name__)


class SheetsClient(SheetsClientPort):
    def open_spreadsheet(self, credentials_path: Path, spreadsheet_id: str) -> gspread.Spreadsheet:
        logger.info("Conectando a Google Sheets con credenciales: %s", credentials_path)
        try:
            client = gspread.service_account(filename=str(credentials_path))
            return client.open_by_key(spreadsheet_id)
        except Exception as exc:
            raise map_gspread_exception(exc) from exc
