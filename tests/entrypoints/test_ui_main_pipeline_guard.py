from __future__ import annotations

import pytest

from app.entrypoints.diagnostico_widgets import validar_ventana_creada


def test_validar_ventana_creada_none_lanza_error_controlado() -> None:
    with pytest.raises(RuntimeError, match="VENTANA_ARRANQUE_NO_CREADA"):
        validar_ventana_creada(None)


def test_validar_ventana_creada_objeto_dummy_no_lanza() -> None:
    validar_ventana_creada(object())
