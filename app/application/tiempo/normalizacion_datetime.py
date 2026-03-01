from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo


TZ_POR_DEFECTO = "Europe/Madrid"


def parsear_iso_datetime(texto: str, tz_por_defecto: str = TZ_POR_DEFECTO) -> datetime:
    fecha = datetime.fromisoformat(texto)
    if fecha.tzinfo is not None:
        return fecha
    return fecha.replace(tzinfo=ZoneInfo(tz_por_defecto))


def duracion_ms(inicio: datetime, fin: datetime) -> int:
    inicio_aware = _normalizar_aware(inicio)
    fin_aware = _normalizar_aware(fin)
    diferencia = fin_aware.astimezone(UTC) - inicio_aware.astimezone(UTC)
    return max(0, int(diferencia.total_seconds() * 1000))


def _normalizar_aware(valor: datetime) -> datetime:
    if valor.tzinfo is not None:
        return valor
    return valor.replace(tzinfo=UTC)
