from __future__ import annotations

import json
import logging
import os
import uuid
from pathlib import Path

from app.domain.models import SheetsConfig

logger = logging.getLogger(__name__)


def resolve_appdata_dir() -> Path:
    env_dir = os.environ.get("LOCALAPPDATA")
    if env_dir:
        base_dir = Path(env_dir)
    else:
        base_dir = Path.home() / ".local" / "share"
    return base_dir / "HorasSindicales"


class SheetsConfigStore:
    def __init__(self, base_dir: Path | None = None) -> None:
        self._base_dir = base_dir or resolve_appdata_dir()
        self._config_path = self._base_dir / "config.json"
        self._credentials_path = self._base_dir / "secrets" / "credentials.json"

    def load(self) -> SheetsConfig | None:
        if not self._config_path.exists():
            return None
        try:
            payload = json.loads(self._config_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.exception("No se pudo leer config.json: %s", exc)
            return None
        spreadsheet_id = str(payload.get("sheets_spreadsheet_id", "")).strip()
        credentials_path = str(payload.get("path_credentials_json", "")).strip()
        device_id = str(payload.get("device_id", "")).strip()
        if not device_id:
            device_id = self._generate_device_id()
            payload["device_id"] = device_id
            self._write_payload(payload)
        if not spreadsheet_id and not credentials_path:
            return None
        return SheetsConfig(
            spreadsheet_id=spreadsheet_id,
            credentials_path=credentials_path,
            device_id=device_id,
        )

    def save(self, config: SheetsConfig) -> SheetsConfig:
        payload = {
            "sheets_spreadsheet_id": config.spreadsheet_id,
            "path_credentials_json": config.credentials_path,
            "device_id": config.device_id or self._generate_device_id(),
        }
        self._write_payload(payload)
        return SheetsConfig(
            spreadsheet_id=payload["sheets_spreadsheet_id"],
            credentials_path=payload["path_credentials_json"],
            device_id=payload["device_id"],
        )

    def credentials_path(self) -> Path:
        return self._credentials_path

    def _write_payload(self, payload: dict[str, str]) -> None:
        self._config_path.parent.mkdir(parents=True, exist_ok=True)
        self._config_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    @staticmethod
    def _generate_device_id() -> str:
        return str(uuid.uuid4())
