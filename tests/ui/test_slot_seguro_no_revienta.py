from __future__ import annotations

import logging

import pytest

from app.ui.qt.slot_seguro import envolver_slot_seguro


pytestmark = pytest.mark.headless_safe


class ToastQueFalla:
    def __init__(self) -> None:
        self.llamadas = 0

    def error(self, mensaje: str, **kwargs: object) -> None:
        self.llamadas += 1
        raise ValueError("toast_error")


def test_slot_falla_y_toast_falla_no_propaga_excepcion() -> None:
    toast = ToastQueFalla()

    def handler() -> None:
        raise RuntimeError("boom")

    slot = envolver_slot_seguro(
        handler,
        contexto="builder:test",
        logger=logging.getLogger("test.slot.toast.fallo"),
        toast=toast,
    )

    slot()

    assert toast.llamadas == 1
