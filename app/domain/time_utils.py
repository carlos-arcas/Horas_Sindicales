from __future__ import annotations

from numbers import Real
import math
import re


def hm_to_minutes(horas: int, minutos: int) -> int:
    """Normaliza una pareja horas/minutos a minutos totales no negativos."""
    if horas < 0 or minutos < 0:
        raise ValueError("Horas y minutos deben ser no negativos.")
    return horas * 60 + minutos


def minutes_to_hm(minutos: int) -> tuple[int, int]:
    if minutos < 0:
        raise ValueError("Los minutos deben ser no negativos.")
    horas = minutos // 60
    mins = minutos % 60
    return horas, mins


def parse_hhmm(valor: str) -> int:
    """Parsea texto HH:MM con validación estricta de rango horario.

    Se usa una validación estricta para detectar errores de captura en origen en
    lugar de corregirlos silenciosamente, evitando cálculos inconsistentes.
    """
    partes = valor.strip().split(":")
    if len(partes) != 2:
        raise ValueError("Formato inválido, use HH:MM.")
    horas = int(partes[0])
    minutos = int(partes[1])
    if horas < 0 or horas > 23 or minutos < 0 or minutos > 59:
        raise ValueError("Hora fuera de rango.")
    return hm_to_minutes(horas, minutos)


def _normalize_minutes_input(minutos: int | float | str | None) -> int:
    """Acepta minutos en int/float y redondea al minuto más cercano.

    Política: se aplica ``int(round(minutos))`` para floats.
    """
    if minutos is None:
        return 0
    if isinstance(minutos, str):
        valor = minutos.strip()
        if not re.fullmatch(r"[-+]?\d+(?:\.\d+)?", valor):
            raise ValueError("'minutos' debe ser un número válido (int, float o string numérica).")
        minutos = float(valor)
    if isinstance(minutos, bool) or not isinstance(minutos, Real):
        raise ValueError("'minutos' debe ser un número válido (int, float o string numérica).")
    minutos_float = float(minutos)
    if math.isnan(minutos_float):
        return 0
    if minutos_float < 0:
        raise ValueError("Los minutos deben ser no negativos.")

    return int(round(minutos_float))


def minutes_to_hhmm(minutos: int | float | str | None) -> str:
    minutos_normalizados = _normalize_minutes_input(minutos)
    horas, mins = minutes_to_hm(minutos_normalizados)
    return f"{horas:02d}:{mins:02d}"
