from __future__ import annotations

import logging
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from app.domain.models import SheetsConfig
from app.domain.ports import SheetsConfigStorePort, SheetsGatewayPort
from app.domain.services import BusinessRuleError, ValidacionError, validar_sheets_config
from app.domain.sheets_errors import SheetsCredentialsError

logger = logging.getLogger(__name__)

SHEETS_SCHEMA: dict[str, list[str]] = {
    "delegadas": [
        "uuid",
        "nombre",
        "genero",
        "activa",
        "bolsa_mes_min",
        "bolsa_anual_min",
        "updated_at",
        "source_device",
        "deleted",
    ],
    "solicitudes": [
        "uuid",
        "delegada_uuid",
        "Delegada",
        "fecha",
        "desde_h",
        "desde_m",
        "hasta_h",
        "hasta_m",
        "completo",
        "minutos_total",
        "notas",
        "estado",
        "created_at",
        "updated_at",
        "source_device",
        "deleted",
        "pdf_id",
    ],
    "cuadrantes": [
        "uuid",
        "delegada_uuid",
        "dia_semana",
        "man_h",
        "man_m",
        "tar_h",
        "tar_m",
        "updated_at",
        "source_device",
        "deleted",
    ],
    "pdf_log": [
        "pdf_id",
        "delegada_uuid",
        "rango_fechas",
        "fecha_generacion",
        "hash",
        "updated_at",
        "source_device",
    ],
    "config": [
        "key",
        "value",
        "updated_at",
        "source_device",
    ],
}


@dataclass(frozen=True)
class SheetsConnectionResult:
    spreadsheet_title: str
    spreadsheet_id: str
    schema_actions: list[str]


class SheetsService:
    def __init__(
        self,
        config_repo: SheetsConfigStorePort,
        gateway: SheetsGatewayPort,
    ) -> None:
        self._config_repo = config_repo
        self._gateway = gateway

    def get_config(self) -> SheetsConfig | None:
        return self._config_repo.load()

    def credentials_path(self) -> Path:
        return self._config_repo.credentials_path()

    def store_credentials(self, source_path: str) -> Path:
        destination = self.credentials_path()
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, destination)
        logger.info("Credenciales copiadas a %s", destination)
        return destination

    def save_config(self, spreadsheet_input: str, credentials_path: str | None = None) -> SheetsConfig:
        spreadsheet_id = self._normalize_spreadsheet_id(spreadsheet_input)
        if credentials_path:
            credentials = credentials_path
        else:
            current = self._config_repo.load()
            credentials = current.credentials_path if current else ""
        config = SheetsConfig(
            spreadsheet_id=spreadsheet_id,
            credentials_path=credentials,
            device_id=self._ensure_device_id(),
        )
        try:
            validar_sheets_config(config)
        except ValidacionError as exc:
            raise BusinessRuleError(str(exc)) from exc
        saved = self._config_repo.save(config)
        logger.info("Configuración de Sheets guardada.")
        return saved

    def test_connection(self, spreadsheet_input: str, credentials_path: str | None = None) -> SheetsConnectionResult:
        config = self.save_config(spreadsheet_input, credentials_path)
        self._validate_credentials_file(config.credentials_path)
        title, spreadsheet_id, actions = self._gateway.test_connection(config, SHEETS_SCHEMA)
        logger.info("Conexión OK. Spreadsheet: %s (%s)", title, spreadsheet_id)
        return SheetsConnectionResult(
            spreadsheet_title=title,
            spreadsheet_id=spreadsheet_id,
            schema_actions=actions,
        )

    def _ensure_device_id(self) -> str:
        current = self._config_repo.load()
        if current and current.device_id:
            return current.device_id
        return ""

    @staticmethod
    def _normalize_spreadsheet_id(value: str) -> str:
        raw = value.strip()
        if not raw:
            return ""
        if "docs.google.com" in raw:
            match = re.search(r"/d/([a-zA-Z0-9-_]+)", raw)
            if match:
                return match.group(1)
        return raw

    @staticmethod
    def _validate_credentials_file(path: str) -> None:
        if not path:
            raise BusinessRuleError("Debe seleccionar un archivo de credenciales JSON.")
        credentials_path = Path(path)
        if not credentials_path.exists():
            raise SheetsCredentialsError(f"No se encuentra credentials.json en {credentials_path}.")
