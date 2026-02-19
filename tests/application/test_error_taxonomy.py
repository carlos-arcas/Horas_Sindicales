from __future__ import annotations

import pytest

from app.core.errors import PersistenceError, ValidationError
from app.ui.error_mapping import map_error_to_user_message


def test_persistence_error_propagates_in_confirmar_sin_pdf(solicitud_use_cases, solicitud_dto) -> None:
    def _raise_persistence(*args, **kwargs):
        raise PersistenceError("db down")

    solicitud_use_cases._repo.mark_generated = _raise_persistence  # type: ignore[method-assign]

    with pytest.raises(PersistenceError):
        solicitud_use_cases.confirmar_sin_pdf([solicitud_dto])


def test_validation_error_uses_functional_message_in_ui_mapping() -> None:
    error = ValidationError("La fecha es obligatoria")

    assert map_error_to_user_message(error) == "La fecha es obligatoria"
