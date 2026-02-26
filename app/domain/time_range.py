from __future__ import annotations

from app.core.errors import ValidationError
from app.domain.time_utils import parse_hhmm

DAY_START_MIN = 0
DAY_END_MIN = 24 * 60


class TimeRangeValidationError(ValidationError):
    """Error de validación de tramos horarios.

    Nota para junior: el sistema usa intervalos semiabiertos [inicio, fin).
    Eso significa que el minuto `fin` no pertenece al tramo. Así evitamos
    falsos solapes en franjas contiguas (10:00-11:00 y 11:00-12:00).
    """


def overlaps(a_start: int, a_end: int, b_start: int, b_end: int) -> bool:
    """Devuelve True si dos tramos [inicio, fin) se solapan."""

    return a_start < b_end and b_start < a_end


def normalize_range(
    *,
    completo: bool,
    desde: str | None = None,
    hasta: str | None = None,
    desde_min: int | None = None,
    hasta_min: int | None = None,
) -> tuple[int, int]:
    """Normaliza el tramo a minutos canónicos [inicio, fin).

    Reglas:
    - completo=True => [00:00, 24:00)
    - completo=False requiere desde/hasta válidos con duración positiva.
    - 00:00-00:00 NO representa día completo salvo que completo=True.
    """

    if completo:
        return DAY_START_MIN, DAY_END_MIN

    start = desde_min if desde_min is not None else (parse_hhmm(desde) if desde else None)
    end = hasta_min if hasta_min is not None else (parse_hhmm(hasta) if hasta else None)

    if start is None or end is None:
        raise TimeRangeValidationError("Desde y hasta son obligatorios para solicitudes parciales.")
    if end <= start:
        raise TimeRangeValidationError("La solicitud parcial debe tener una duración mayor de 0 minutos.")

    return start, end
