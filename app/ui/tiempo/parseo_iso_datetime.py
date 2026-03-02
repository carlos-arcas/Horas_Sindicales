from __future__ import annotations

import logging
from datetime import UTC, datetime, tzinfo


logger = logging.getLogger(__name__)


def _zona_horaria_local() -> tzinfo:
    return datetime.now().astimezone().tzinfo or UTC


def parsear_iso_datetime(iso: str) -> datetime:
    try:
        return datetime.fromisoformat(iso)
    except ValueError:
        logger.warning(
            "iso_datetime_invalido",
            extra={"evento": "iso_datetime_invalido", "iso": iso[:128]},
        )
        raise


def normalizar_zona_horaria(dt: datetime, tz_objetivo: tzinfo) -> datetime:
    if dt.tzinfo is None:
        tz_local = _zona_horaria_local()
        logger.info(
            "normalizacion_tz_naive_local",
            extra={
                "evento": "normalizacion_tz_naive_local",
                "tz_local": str(tz_local),
                "tz_objetivo": str(tz_objetivo),
            },
        )
        return dt.replace(tzinfo=tz_local).astimezone(tz_objetivo)
    return dt.astimezone(tz_objetivo)


def duracion_ms_desde_iso(
    inicio_iso: str, fin_iso: str, *, tz_objetivo: tzinfo | None = None
) -> int:
    zona_objetivo = tz_objetivo or _zona_horaria_local()
    try:
        inicio = normalizar_zona_horaria(parsear_iso_datetime(inicio_iso), zona_objetivo)
        fin = normalizar_zona_horaria(parsear_iso_datetime(fin_iso), zona_objetivo)
    except (TypeError, ValueError):
        return 0
    return max(0, int((fin - inicio).total_seconds() * 1000))
