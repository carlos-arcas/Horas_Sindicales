from __future__ import annotations

from datetime import datetime


def normalize_date(value: str | None) -> str | None:
    if not value:
        return None
    raw = value.strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y", "%d-%m-%y"):
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return raw if len(raw) == 10 else None


def normalize_hhmm(value: str | None) -> str | None:
    if not value:
        return None
    raw = value.strip()
    if ":" in raw:
        parts = raw.split(":")
        if len(parts) >= 2 and parts[0].strip().isdigit() and parts[1].strip().isdigit():
            return f"{int(parts[0]):02d}:{int(parts[1]):02d}"
    if raw.isdigit():
        num = int(raw)
        return f"{num // 60:02d}:{num % 60:02d}"
    return None


def solicitud_unique_key(
    delegada_uuid: str | None,
    fecha: str | None,
    completo: bool,
    desde_hhmm: str | None,
    hasta_hhmm: str | None,
) -> tuple[str, str, bool, str | None, str | None] | None:
    if not delegada_uuid:
        return None
    norm_fecha = normalize_date(fecha)
    if not norm_fecha:
        return None
    return (
        delegada_uuid.strip(),
        norm_fecha,
        bool(completo),
        normalize_hhmm(desde_hhmm),
        normalize_hhmm(hasta_hhmm),
    )
