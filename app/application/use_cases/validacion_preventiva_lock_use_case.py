from __future__ import annotations

from collections.abc import Callable

from app.application.ports.db_lock_error_classifier import DbLockErrorClassifier


class _NeverLockedClassifier:
    def is_locked_error(self, error: Exception) -> bool:
        return False


class ValidacionPreventivaLockUseCase:
    def __init__(self, classifier: DbLockErrorClassifier | None = None) -> None:
        self._classifier = classifier or _NeverLockedClassifier()

    def ejecutar(self, operacion: Callable[[], None]) -> Exception | None:
        try:
            operacion()
            return None
        except Exception as exc:  # noqa: BLE001
            if self._classifier.is_locked_error(exc):
                return exc
            raise
