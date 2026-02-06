from __future__ import annotations

import logging
from pathlib import Path

import gspread

logger = logging.getLogger(__name__)


class SheetsClient:
    def open_spreadsheet(self, credentials_path: Path, spreadsheet_id: str) -> gspread.Spreadsheet:
        logger.info("Conectando a Google Sheets con credenciales: %s", credentials_path)
        client = gspread.service_account(filename=str(credentials_path))
        return client.open_by_key(spreadsheet_id)
