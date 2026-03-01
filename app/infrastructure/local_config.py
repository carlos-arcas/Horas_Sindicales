from __future__ import annotations

import configparser
import json
import logging
import os
import uuid
from pathlib import Path

from aplicacion.puertos.repositorio_preferencias import IRepositorioPreferencias
from app.application.ports.sistema_archivos_puerto import DocumentoNoEncontradoError, ProveedorDocumentosPuerto
from app.bootstrap.logging import log_operational_error
from app.domain.models import SheetsConfig

logger = logging.getLogger(__name__)

_SECTION_PREFERENCIAS = "preferencias"


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


class ProveedorDocumentosRepositorio(ProveedorDocumentosPuerto):
    _NOMBRE_GUIA_SYNC = "guia_sync_paso_a_paso.md"

    def __init__(self, raiz_repo: Path | None = None) -> None:
        self._raiz_repo = raiz_repo.resolve() if raiz_repo else self._detectar_raiz_repo()

    def obtener_ruta_guia_sync(self) -> str:
        ruta = self._raiz_repo / "docs" / self._NOMBRE_GUIA_SYNC
        if not ruta.is_file():
            raise DocumentoNoEncontradoError(
                "No se encontró la guía de Sync en la ruta esperada: "
                f"{ruta.as_posix()}"
            )
        return ruta.as_posix()

    @staticmethod
    def _detectar_raiz_repo() -> Path:
        actual = Path(__file__).resolve()
        for candidato in actual.parents:
            if (candidato / ".git").exists() and (candidato / "docs").is_dir():
                return candidato

        raise DocumentoNoEncontradoError(
            "No se pudo detectar la raíz del repositorio para resolver documentos."
        )


class RepositorioPreferenciasIni(IRepositorioPreferencias):
    """Implementación headless para persistir preferencias de UI en formato INI."""

    def __init__(self, ruta_archivo: Path | None = None) -> None:
        self._ruta_archivo = (
            ruta_archivo or (Path.home() / ".horas_sindicales" / "preferencias.ini")
        )

    def obtener_bool(self, clave: str, por_defecto: bool) -> bool:
        parser = self._cargar_parser()
        if not parser.has_option(_SECTION_PREFERENCIAS, clave):
            return por_defecto
        try:
            return parser.getboolean(_SECTION_PREFERENCIAS, clave)
        except ValueError:
            log_operational_error(
                logger,
                "Valor booleano inválido en preferencias INI; se usa por defecto.",
                extra={"clave": clave, "por_defecto": por_defecto},
            )
            return por_defecto

    def guardar_bool(self, clave: str, valor: bool) -> None:
        parser = self._cargar_parser()
        if not parser.has_section(_SECTION_PREFERENCIAS):
            parser.add_section(_SECTION_PREFERENCIAS)
        parser[_SECTION_PREFERENCIAS][clave] = "true" if bool(valor) else "false"
        self._guardar_parser(parser)

    def obtener_texto(self, clave: str, por_defecto: str) -> str:
        parser = self._cargar_parser()
        return parser.get(_SECTION_PREFERENCIAS, clave, fallback=por_defecto)

    def guardar_texto(self, clave: str, valor: str) -> None:
        parser = self._cargar_parser()
        if not parser.has_section(_SECTION_PREFERENCIAS):
            parser.add_section(_SECTION_PREFERENCIAS)
        parser[_SECTION_PREFERENCIAS][clave] = str(valor)
        self._guardar_parser(parser)

    def _cargar_parser(self) -> configparser.ConfigParser:
        parser = configparser.ConfigParser()
        if self._ruta_archivo.exists():
            parser.read(self._ruta_archivo, encoding="utf-8")
        if not parser.has_section(_SECTION_PREFERENCIAS):
            parser.add_section(_SECTION_PREFERENCIAS)
        return parser

    def _guardar_parser(self, parser: configparser.ConfigParser) -> None:
        try:
            self._ruta_archivo.parent.mkdir(parents=True, exist_ok=True)
            with self._ruta_archivo.open("w", encoding="utf-8") as archivo:
                parser.write(archivo)
        except OSError as exc:  # pragma: no cover - error IO del sistema
            log_operational_error(
                logger,
                "Error guardando preferencias INI.",
                exc=exc,
                extra={"ruta": str(self._ruta_archivo)},
            )
            raise
