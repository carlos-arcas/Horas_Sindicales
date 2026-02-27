from __future__ import annotations

from typing import Any

from app.infrastructure.sheets_errors import SheetsApiCompatibilityError


def normalize_batch_get_result(ranges: list[str], values_by_range: Any) -> dict[str, list[list[str]]]:
    mapped: dict[str, list[list[str]]] = {range_name: [] for range_name in ranges}
    if isinstance(values_by_range, dict):
        return _normalize_from_dict(mapped, values_by_range)
    if isinstance(values_by_range, list):
        return _normalize_from_list(mapped, ranges, values_by_range)
    raise SheetsApiCompatibilityError("Versión de gspread no soporta batch_get; usa values_batch_get")


def worksheet_name_from_range(range_name: str) -> str | None:
    if "!" in range_name:
        sheet_part = range_name.split("!", 1)[0].strip()
    else:
        sheet_part = range_name.strip()
    if not sheet_part:
        return None
    if sheet_part.startswith("'") and sheet_part.endswith("'"):
        return sheet_part[1:-1].replace("''", "'")
    return sheet_part


def worksheet_from_operation_name(operation_name: str) -> str | None:
    start = operation_name.find("(")
    end = operation_name.rfind(")")
    if start < 0 or end <= start:
        return None
    worksheet_name = operation_name[start + 1 : end].strip()
    return worksheet_name or None


def _normalize_from_dict(
    mapped: dict[str, list[list[str]]],
    values_by_range: dict[str, Any],
) -> dict[str, list[list[str]]]:
    value_ranges = values_by_range.get("valueRanges", [])
    if not isinstance(value_ranges, list):
        return mapped
    for value_range in value_ranges:
        if not isinstance(value_range, dict):
            continue
        range_name = value_range.get("range")
        if not isinstance(range_name, str):
            continue
        values = value_range.get("values", [])
        mapped[range_name] = values if isinstance(values, list) else []
    return mapped


def _normalize_from_list(
    mapped: dict[str, list[list[str]]],
    ranges: list[str],
    values_by_range: list[Any],
) -> dict[str, list[list[str]]]:
    for range_name, values in zip(ranges, values_by_range):
        mapped[range_name] = values if isinstance(values, list) else []
    return mapped


def should_retry_rate_limit(attempt: int, max_retries: int) -> bool:
    return attempt < max_retries


def write_backoff_seconds(attempt: int) -> int:
    return 2 ** (attempt - 1)


def read_backoff_seconds(attempt: int, base_seconds: int) -> int:
    return base_seconds * (2 ** (attempt - 1))
