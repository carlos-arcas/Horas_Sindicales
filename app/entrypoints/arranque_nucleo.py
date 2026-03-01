from __future__ import annotations

import configparser
import os
from pathlib import Path

from aplicacion.dtos.resultado_arranque import ResultadoArranqueDTO

_SECTION_PREFERENCIAS = "ui"
_CLAVE_IDIOMA = "idioma_ui"
_CLAVE_PANTALLA_COMPLETA = "pantalla_completa"
_CLAVE_ONBOARDING = "onboarding_completado"



def _ruta_preferencias() -> Path:
    return Path.home() / ".horas_sindicales" / "preferencias.ini"



def _leer_parser_preferencias() -> configparser.ConfigParser:
    parser = configparser.ConfigParser()
    ruta = _ruta_preferencias()
    if ruta.exists():
        parser.read(ruta, encoding="utf-8")
    if not parser.has_section(_SECTION_PREFERENCIAS):
        parser.add_section(_SECTION_PREFERENCIAS)
    return parser



def _leer_idioma(parser: configparser.ConfigParser) -> str:
    idioma_env = os.getenv("HORAS_UI_IDIOMA", "").strip().lower()
    if idioma_env in {"es", "en"}:
        return idioma_env
    idioma_ini = parser.get(_SECTION_PREFERENCIAS, _CLAVE_IDIOMA, fallback="es").strip().lower()
    if idioma_ini in {"es", "en"}:
        return idioma_ini
    return "es"



def _leer_bool(parser: configparser.ConfigParser, clave: str, por_defecto: bool) -> bool:
    try:
        return parser.getboolean(_SECTION_PREFERENCIAS, clave, fallback=por_defecto)
    except ValueError:
        return por_defecto



def ejecutar_arranque_puro() -> ResultadoArranqueDTO:
    parser = _leer_parser_preferencias()
    onboarding_completado = _leer_bool(parser, _CLAVE_ONBOARDING, False)
    return ResultadoArranqueDTO(
        idioma_inicial=_leer_idioma(parser),
        pantalla_completa_inicial=_leer_bool(parser, _CLAVE_PANTALLA_COMPLETA, False),
        necesita_onboarding=not onboarding_completado,
    )
