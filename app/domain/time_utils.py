from __future__ import annotations


def hm_to_minutes(horas: int, minutos: int) -> int:
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
    partes = valor.strip().split(":")
    if len(partes) != 2:
        raise ValueError("Formato inválido, use HH:MM.")
    horas = int(partes[0])
    minutos = int(partes[1])
    if horas < 0 or horas > 23 or minutos < 0 or minutos > 59:
        raise ValueError("Hora fuera de rango.")
    return hm_to_minutes(horas, minutos)


def minutes_to_hhmm(minutos: int) -> str:
    horas, mins = minutes_to_hm(minutos)
    return f"{horas:02d}:{mins:02d}"
