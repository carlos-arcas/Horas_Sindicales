from __future__ import annotations

import logging

from app.ui.qt.slot_seguro import envolver_slot_seguro


class ToastFalso:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def error(self, mensaje: str, **kwargs: object) -> None:
        self.calls.append(mensaje)


def test_envolver_slot_seguro_atrapa_excepcion_y_loguea(caplog) -> None:
    def handler() -> None:
        raise RuntimeError("boom")

    slot = envolver_slot_seguro(handler, contexto="builder:test", logger=logging.getLogger("test.slot"))

    with caplog.at_level(logging.ERROR):
        slot()

    assert "qt_slot_exception" in caplog.text
    registro = caplog.records[-1]
    assert registro.reason_code == "QT_SLOT_EXCEPTION"
    assert registro.contexto == "builder:test"


def test_envolver_slot_seguro_notifica_toast_si_esta_disponible() -> None:
    toast = ToastFalso()

    def handler() -> None:
        raise ValueError("fallo")

    slot = envolver_slot_seguro(
        handler,
        contexto="builder:test",
        logger=logging.getLogger("test.slot.toast"),
        toast=toast,
    )

    slot()

    assert len(toast.calls) == 1
    assert toast.calls[0]
