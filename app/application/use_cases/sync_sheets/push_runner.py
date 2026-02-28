from __future__ import annotations

from collections.abc import Callable
from typing import Any


def run_with_retries(operation: Callable[[], Any], *, retries: int = 1) -> Any:
    attempt = 0
    while True:
        try:
            return operation()
        except Exception:
            attempt += 1
            if attempt >= retries:
                raise


def run_push_values_update(worksheet: Any, values: list[list[Any]] | tuple[tuple[Any, ...], ...], *, retries: int = 1) -> None:
    def _update() -> None:
        worksheet.update("A1", [list(row) for row in values])

    run_with_retries(_update, retries=retries)
