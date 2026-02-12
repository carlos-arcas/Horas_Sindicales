from __future__ import annotations

from datetime import datetime


def normalize_date(value: str | None) -> str | None:
    if not value:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(raw, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return raw if len(raw) == 10 and raw[4] == "-" and raw[7] == "-" else None


def normalize_hhmm(value: str | None) -> str | None:
    if value is None:
        return None
    raw = str(value).strip()
    if raw == "":
        return None
    if ":" in raw:
        hh, mm = raw.split(":", 1)
    else:
        hh, mm = raw, "0"
    try:
        hours = int(hh)
        minutes = int(mm)
    except ValueError:
        return None
    if hours < 0 or minutes < 0 or minutes > 59:
        return None
    return f"{hours:02d}:{minutes:02d}"


def solicitud_unique_key(
    delegada_uuid: str | None,
    fecha: str | None,
    completo: bool,
    desde: str | None,
    hasta: str | None,
) -> tuple[str, str, bool, str, str] | None:
    if not delegada_uuid:
        return None
    normalized_date = normalize_date(fecha)
    if not normalized_date:
        return None
    desde_norm = normalize_hhmm(desde) if not completo else ""
    hasta_norm = normalize_hhmm(hasta) if not completo else ""
    return (delegada_uuid.strip(), normalized_date, bool(completo), desde_norm or "", hasta_norm or "")
