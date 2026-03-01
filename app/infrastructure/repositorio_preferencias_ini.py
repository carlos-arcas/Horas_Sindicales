"""Repositorio de preferencias persistido en archivo INI sin dependencias Qt."""

from __future__ import annotations

import configparser
import logging
from pathlib import Path

from aplicacion.puertos.repositorio_preferencias import IRepositorioPreferencias
from app.bootstrap.logging import log_operational_error

LOGGER = logging.getLogger(__name__)

_SECTION = "preferencias"


class RepositorioPreferenciasIni(IRepositorioPreferencias):
    """Implementación headless para persistir preferencias de UI en formato INI."""

    def __init__(self, ruta_archivo: Path | None = None) -> None:
        self._ruta_archivo = ruta_archivo or (Path.home() / ".horas_sindicales" / "preferencias.ini")

    def obtener_bool(self, clave: str, por_defecto: bool) -> bool:
        parser = self._cargar_parser()
        if not parser.has_option(_SECTION, clave):
            return por_defecto
        try:
            return parser.getboolean(_SECTION, clave)
        except ValueError:
            log_operational_error(
                LOGGER,
                "Valor booleano inválido en preferencias INI; se usa por defecto.",
                extra={"clave": clave, "por_defecto": por_defecto},
            )
            return por_defecto

    def guardar_bool(self, clave: str, valor: bool) -> None:
        parser = self._cargar_parser()
        if not parser.has_section(_SECTION):
            parser.add_section(_SECTION)
        parser[_SECTION][clave] = "true" if bool(valor) else "false"
        self._guardar_parser(parser)

    def obtener_texto(self, clave: str, por_defecto: str) -> str:
        parser = self._cargar_parser()
        return parser.get(_SECTION, clave, fallback=por_defecto)

    def guardar_texto(self, clave: str, valor: str) -> None:
        parser = self._cargar_parser()
        if not parser.has_section(_SECTION):
            parser.add_section(_SECTION)
        parser[_SECTION][clave] = str(valor)
        self._guardar_parser(parser)

    def _cargar_parser(self) -> configparser.ConfigParser:
        parser = configparser.ConfigParser()
        if self._ruta_archivo.exists():
            parser.read(self._ruta_archivo, encoding="utf-8")
        if not parser.has_section(_SECTION):
            parser.add_section(_SECTION)
        return parser

    def _guardar_parser(self, parser: configparser.ConfigParser) -> None:
        try:
            self._ruta_archivo.parent.mkdir(parents=True, exist_ok=True)
            with self._ruta_archivo.open("w", encoding="utf-8") as archivo:
                parser.write(archivo)
        except OSError as exc:  # pragma: no cover - error IO del sistema
            log_operational_error(
                LOGGER,
                "Error guardando preferencias INI.",
                exc=exc,
                extra={"ruta": str(self._ruta_archivo)},
            )
            raise
