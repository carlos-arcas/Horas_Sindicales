from __future__ import annotations

import re
from typing import Any


_RANGE_RE = re.compile(
    r"^(?P<sheet>'(?:[^']|'')+'|[^!]+)!(?P<start_col>[A-Za-z]+)(?P<start_row>\d+)(?::(?P<end_col>[A-Za-z]+)(?P<end_row>\d+))?$"
)


def parse_a1_range(range_name: str) -> tuple[str, str, int, str, int]:
    """Parsea un rango A1 completo y retorna datos normalizados."""
    cleaned = str(range_name).strip()
    match = _RANGE_RE.match(cleaned)
    if not match:
        raise ValueError(f"Rango A1 inválido: {range_name!r}")

    sheet = _normalize_sheet_name(match.group("sheet"))
    start_col = match.group("start_col").upper()
    start_row = int(match.group("start_row"))
    end_col = (match.group("end_col") or start_col).upper()
    end_row = int(match.group("end_row") or start_row)
    if start_row <= 0 or end_row <= 0:
        raise ValueError(f"Rango A1 inválido: {range_name!r}")
    return sheet, start_col, start_row, end_col, end_row


def _normalize_sheet_name(raw_name: str) -> str:
    name = raw_name.strip()
    if name.startswith("'") and name.endswith("'") and len(name) >= 2:
        name = name[1:-1].replace("''", "'")
    name = name.strip()
    if not name:
        raise ValueError("Nombre de hoja vacío en rango A1")
    return name


def normalize_cell(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def normalize_headers(headers: list[Any]) -> list[str]:
    normalized: list[str] = []
    for idx, header in enumerate(headers):
        # Comentario para junior: cuando no viene cabecera, le damos un nombre estable.
        clean = normalize_cell(header)
        normalized.append(clean if clean else f"col_{idx + 1}")
    return normalized


def normalize_payload(headers: list[Any], row: list[Any]) -> dict[str, str]:
    normalized_headers = normalize_headers(headers)
    payload: dict[str, str] = {}
    for idx, header in enumerate(normalized_headers):
        payload[header] = normalize_cell(row[idx] if idx < len(row) else "")
    return payload


def is_non_empty_payload(payload: dict[str, Any]) -> bool:
    return any(normalize_cell(value) for value in payload.values())


def normalize_rows(values: list[list[Any]]) -> list[tuple[int, dict[str, str]]]:
    if not values:
        return []
    headers = values[0]
    rows: list[tuple[int, dict[str, str]]] = []
    for row_number, row in enumerate(values[1:], start=2):
        payload = normalize_payload(headers, row)
        if is_non_empty_payload(payload):
            rows.append((row_number, payload))
    return rows


def ensure_headers(headers: list[str], row: dict[str, Any]) -> list[str]:
    return headers if headers else [str(key).strip() for key in row.keys()]


def find_uuid_row(records: list[dict[str, Any]], uuid_value: str) -> int | None:
    uuid_clean = normalize_cell(uuid_value)
    if not uuid_clean:
        return None
    for idx, record in enumerate(records, start=2):
        if normalize_cell(record.get("uuid", "")) == uuid_clean:
            return idx
    return None


def merge_values_for_upsert(headers: list[str], row: dict[str, Any], fallback: dict[str, Any] | None = None) -> list[Any]:
    base = fallback or {}
    return [row.get(header, base.get(header, "")) for header in headers]


def ensure_uuid_header(headers: list[str]) -> tuple[list[str], bool]:
    if "uuid" in headers:
        return headers, False
    return [*headers, "uuid"], True


def map_gateway_error(exc: Exception) -> RuntimeError:
    message = str(exc).strip() or exc.__class__.__name__
    status_code = getattr(exc, "status_code", None)
    response = getattr(exc, "response", None)
    if status_code is None and response is not None:
        status_code = getattr(response, "status_code", None)

    text_lower = message.lower()
    if status_code == 404 or "not found" in text_lower:
        return RuntimeError("No se encontró el spreadsheet o la worksheet solicitada.")
    if status_code == 403 or "permission" in text_lower or "forbidden" in text_lower:
        return RuntimeError("Permisos insuficientes para acceder a Google Sheets.")
    if status_code in {429, 500, 503} or "rate" in text_lower or "quota" in text_lower:
        return RuntimeError("Google Sheets devolvió rate limit o error temporal.")
    return RuntimeError(f"Error de sincronización con Google Sheets: {message}")
