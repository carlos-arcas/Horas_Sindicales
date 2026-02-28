from __future__ import annotations

import sqlite3

import pytest

from app.application.use_cases.validacion_preventiva_lock_use_case import ValidacionPreventivaLockUseCase
from app.infrastructure.sqlite_lock_error_classifier import SQLiteLockErrorClassifier


def test_ejecutar_devuelve_error_cuando_db_esta_bloqueada() -> None:
    use_case = ValidacionPreventivaLockUseCase(SQLiteLockErrorClassifier())

    def operacion() -> None:
        raise sqlite3.OperationalError("database is locked")

    error = use_case.ejecutar(operacion)

    assert isinstance(error, sqlite3.OperationalError)


def test_ejecutar_relanza_error_no_mapeado() -> None:
    use_case = ValidacionPreventivaLockUseCase(SQLiteLockErrorClassifier())

    with pytest.raises(ValueError, match="fallo"):
        use_case.ejecutar(lambda: (_ for _ in ()).throw(ValueError("fallo")))
