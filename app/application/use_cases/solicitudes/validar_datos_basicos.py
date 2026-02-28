from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.application.dto import SolicitudDTO


@dataclass(frozen=True)
class ResultadoValidacionBasica:
    errores: list[str]

    @property
    def es_valido(self) -> bool:
        return not self.errores


def validar_datos_basicos(dto: SolicitudDTO) -> ResultadoValidacionBasica:
    errores: list[str] = []
    errores.extend(_validar_campos_obligatorios(dto))
    errores.extend(_validar_formato_fechas(dto))
    errores.extend(_validar_regla_jornada(dto))
    errores.extend(_validar_limite_horas(dto.horas))
    return ResultadoValidacionBasica(errores=errores)


def _validar_campos_obligatorios(dto: SolicitudDTO) -> list[str]:
    errores: list[str] = []
    if dto.persona_id <= 0:
        errores.append("Debe seleccionar una delegada válida.")
    if not str(dto.fecha_solicitud).strip():
        errores.append("La fecha de solicitud es obligatoria.")
    if not str(dto.fecha_pedida).strip():
        errores.append("La fecha pedida es obligatoria.")
    return errores


def _validar_formato_fechas(dto: SolicitudDTO) -> list[str]:
    errores: list[str] = []
    for campo_fecha in ("fecha_solicitud", "fecha_pedida"):
        valor = getattr(dto, campo_fecha)
        if not valor:
            continue
        try:
            datetime.strptime(valor, "%Y-%m-%d")
        except ValueError:
            errores.append(f"{campo_fecha} debe tener formato YYYY-MM-DD.")
    return errores


def _validar_regla_jornada(dto: SolicitudDTO) -> list[str]:
    if dto.completo:
        return _validar_jornada_completa(dto.horas)
    return _validar_jornada_parcial(dto.desde, dto.hasta)


def _validar_jornada_completa(horas: float) -> list[str]:
    if horas < 0:
        return ["Las horas no pueden ser negativas."]
    return []


def _validar_jornada_parcial(desde: str | None, hasta: str | None) -> list[str]:
    if not desde or not hasta:
        return ["Desde y hasta son obligatorios para peticiones parciales."]

    desde_min = _parse_hhmm_safe(desde)
    hasta_min = _parse_hhmm_safe(hasta)
    if desde_min is None or hasta_min is None:
        return ["Desde/Hasta deben tener formato HH:MM válido."]
    if hasta_min <= desde_min:
        return ["El campo hasta debe ser mayor que desde."]
    return []


def _parse_hhmm_safe(value: str) -> int | None:
    value_norm = value.strip()
    parts = value_norm.split(":")
    if len(parts) != 2:
        return None
    try:
        horas = int(parts[0])
        minutos = int(parts[1])
    except ValueError:
        return None
    if horas < 0 or horas > 23 or minutos < 0 or minutos > 59:
        return None
    return horas * 60 + minutos


def _validar_limite_horas(horas: float) -> list[str]:
    if horas > 24:
        return ["Las horas no pueden superar 24 en una sola petición."]
    return []
