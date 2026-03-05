from __future__ import annotations

import logging
import sys
from types import SimpleNamespace

import pytest

from app.ui.qt_hilos import detener_y_destruir_timer_seguro




@pytest.fixture(autouse=True)
def _stub_shiboken6(monkeypatch):
    monkeypatch.setitem(sys.modules, "shiboken6", SimpleNamespace(isValid=lambda _: True))

class FakeTimer:
    def __init__(self, raise_on_stop: bool = False, raise_on_delete: bool = False) -> None:
        self.stop_called = 0
        self.delete_called = 0
        self.raise_on_stop = raise_on_stop
        self.raise_on_delete = raise_on_delete

    def stop(self) -> None:
        self.stop_called += 1
        if self.raise_on_stop:
            raise RuntimeError("already deleted")

    def deleteLater(self) -> None:
        self.delete_called += 1
        if self.raise_on_delete:
            raise RuntimeError("already deleted")


def test_detener_y_destruir_timer_seguro_con_none_no_lanza() -> None:
    detener_y_destruir_timer_seguro(
        None,
        nombre="watchdog",
        logger=logging.getLogger(__name__),
        marcar_stage=lambda _stage: None,
    )


def test_detener_y_destruir_timer_seguro_detiene_y_elimina() -> None:
    timer = FakeTimer()
    stages: list[str] = []

    detener_y_destruir_timer_seguro(
        timer,
        nombre="watchdog",
        logger=logging.getLogger(__name__),
        marcar_stage=stages.append,
    )

    assert timer.stop_called == 1
    assert timer.delete_called == 1
    assert "watchdog_stopped" in stages


def test_detener_y_destruir_timer_seguro_si_stop_falla_intenta_delete() -> None:
    timer = FakeTimer(raise_on_stop=True)

    detener_y_destruir_timer_seguro(
        timer,
        nombre="watchdog",
        logger=logging.getLogger(__name__),
        marcar_stage=lambda _stage: None,
    )

    assert timer.stop_called == 1
    assert timer.delete_called == 1


def test_detener_y_destruir_timer_seguro_ignora_runtime_error_en_delete() -> None:
    timer = FakeTimer(raise_on_delete=True)

    detener_y_destruir_timer_seguro(
        timer,
        nombre="watchdog",
        logger=logging.getLogger(__name__),
        marcar_stage=lambda _stage: None,
    )

    assert timer.stop_called == 1
    assert timer.delete_called == 1


def test_detener_y_destruir_timer_seguro_no_toca_timer_invalido(monkeypatch) -> None:
    timer = FakeTimer()
    monkeypatch.setitem(sys.modules, "shiboken6", SimpleNamespace(isValid=lambda _: False))

    detener_y_destruir_timer_seguro(
        timer,
        nombre="watchdog",
        logger=logging.getLogger(__name__),
        marcar_stage=lambda _stage: None,
    )

    assert timer.stop_called == 0
    assert timer.delete_called == 0
