from __future__ import annotations

import logging
from typing import Any

from app.domain.ports import SqlCursorPort


logger = logging.getLogger(__name__)


def rowcol_to_a1(row: int, col: int) -> str:
    label = ""
    current = col
    while current > 0:
        current, rem = divmod(current - 1, 26)
        label = chr(65 + rem) + label
    return f"{label}{row}"


def execute_with_validation(cursor: SqlCursorPort, sql: str, params: tuple[object, ...], context: str) -> None:
    expected = sql.count("?")
    actual = len(params)
    if expected != actual:
        raise ValueError(
            f"SQL param mismatch for {context}: expected {expected} placeholders, got {actual} parameters."
        )
    cursor.execute(sql, params)


def rows_with_index(
    values: list[list[Any]],
    *,
    worksheet_name: str,
    aliases: dict[str, list[str]] | None = None,
) -> tuple[list[str], list[tuple[int, dict[str, Any]]]]:
    if not values:
        return [], []
    headers = values[0]
    canonical_by_header: dict[str, str] = {}
    if aliases:
        lowered_map: dict[str, str] = {}
        for canonical, names in aliases.items():
            lowered_map[canonical.strip().lower()] = canonical
            for name in names:
                lowered_map[name.strip().lower()] = canonical
        for header in headers:
            key = str(header).strip().lower()
            canonical_by_header[header] = lowered_map.get(key, header)
    rows: list[tuple[int, dict[str, Any]]] = []
    for row_number, row in enumerate(values[1:], start=2):
        if not any(str(cell).strip() for cell in row):
            continue
        payload = {
            headers[i]: row[i] if i < len(row) else ""
            for i in range(len(headers))
            if str(headers[i]).strip()
        }
        if canonical_by_header:
            canonical_payload: dict[str, Any] = {}
            for original_key, value in payload.items():
                canonical_key = canonical_by_header.get(original_key, original_key)
                if canonical_key not in canonical_payload or not str(canonical_payload.get(canonical_key, "")).strip():
                    canonical_payload[canonical_key] = value
            payload = canonical_payload
        payload["__row_number__"] = row_number
        rows.append((row_number, payload))
    logger.info("Read worksheet=%s filas_leidas=%s", worksheet_name, len(rows))
    return headers, rows
