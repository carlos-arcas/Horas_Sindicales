from __future__ import annotations

from typing import Protocol


class DbLockErrorClassifier(Protocol):
    def is_locked_error(self, error: Exception) -> bool:
        ...
