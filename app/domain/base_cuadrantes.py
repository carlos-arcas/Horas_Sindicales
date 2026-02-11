from __future__ import annotations

from app.domain.time_utils import parse_hhmm

DEFAULT_BASE_START = "09:00"
DEFAULT_BASE_END = "15:00"
DEFAULT_BASE_TURNO = "manana"
DEFAULT_BASE_DIAS = ("lun", "mar", "mie", "jue", "vie")


def _base_duration_minutes() -> int:
    start = parse_hhmm(DEFAULT_BASE_START)
    end = parse_hhmm(DEFAULT_BASE_END)
    if end < start:
        raise ValueError("El horario base debe terminar después de empezar.")
    return end - start


DEFAULT_BASE_MAN_MIN = _base_duration_minutes()
DEFAULT_BASE_TAR_MIN = 0


def default_base_minutes() -> tuple[int, int]:
    return DEFAULT_BASE_MAN_MIN, DEFAULT_BASE_TAR_MIN
