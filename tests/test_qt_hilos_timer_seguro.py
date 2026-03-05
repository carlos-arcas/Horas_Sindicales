from __future__ import annotations

import logging

from app.ui.qt_hilos import detener_y_destruir_timer_seguro


class _TimerFake:
    def __init__(self, *, fallar_stop: bool = False, fallar_delete: bool = False) -> None:
        self.fallar_stop = fallar_stop
        self.fallar_delete = fallar_delete
        self.stop_llamadas = 0
        self.delete_llamadas = 0

    def stop(self) -> None:
        self.stop_llamadas += 1
        if self.fallar_stop:
            raise RuntimeError("already deleted")

    def deleteLater(self) -> None:
        self.delete_llamadas += 1
        if self.fallar_delete:
            raise RuntimeError("already deleted")


def test_detener_y_destruir_timer_seguro_detiene_y_elimina() -> None:
    timer = _TimerFake()
    stages: list[str] = []

    detener_y_destruir_timer_seguro(
        timer,
        nombre="watchdog",
        logger=logging.getLogger(__name__),
        marcar_stage=stages.append,
    )

    assert timer.stop_llamadas == 1
    assert timer.delete_llamadas == 1
    assert "watchdog_stopped" in stages


def test_detener_y_destruir_timer_seguro_ignora_runtime_error() -> None:
    timer = _TimerFake(fallar_stop=True, fallar_delete=True)

    detener_y_destruir_timer_seguro(
        timer,
        nombre="watchdog",
        logger=logging.getLogger(__name__),
        marcar_stage=lambda _stage: None,
    )

    assert timer.stop_llamadas == 1
    assert timer.delete_llamadas == 1
