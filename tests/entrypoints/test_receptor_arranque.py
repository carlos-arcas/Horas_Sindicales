from __future__ import annotations

import importlib
import sys
from types import SimpleNamespace


class _CoordinadorFake:
    def __init__(self) -> None:
        self.stages: list[str] = []
        self.fallback_llamado = 0
        self.finalizar_llamadas: list[object] = []

    def _marcar_boot_stage(self, stage: str) -> None:
        self.stages.append(stage)

    def finalizar_arranque_interfaz(self, resultado: object) -> None:
        self.finalizar_llamadas.append(resultado)
        raise RuntimeError("fallo_ui")

    def _mostrar_fallback_arranque(self) -> None:
        self.fallback_llamado += 1


def test_receptor_recibir_ok_captura_excepcion_y_dispara_fallback(monkeypatch) -> None:
    monkeypatch.setitem(
        sys.modules,
        "PySide6.QtCore",
        SimpleNamespace(QObject=object, Slot=lambda *_args, **_kwargs: (lambda fn: fn)),
    )
    modulo = importlib.import_module("app.entrypoints.receptor_arranque")
    ReceptorArranqueQt = modulo.ReceptorArranqueQt

    coordinador = _CoordinadorFake()
    def scheduler(callback):
        callback()

    receptor = ReceptorArranqueQt(coordinador, scheduler=scheduler)

    receptor.recibir_ok(object())

    assert "receptor_before_delegate" in coordinador.stages
    assert "receptor_delegate_running" in coordinador.stages
    assert "receptor_delegate_exception" in coordinador.stages
    assert coordinador.fallback_llamado == 1


def test_receptor_recibir_ok_programa_una_unica_delegacion(monkeypatch) -> None:
    monkeypatch.setitem(
        sys.modules,
        "PySide6.QtCore",
        SimpleNamespace(QObject=object, Slot=lambda *_args, **_kwargs: (lambda fn: fn)),
    )
    modulo = importlib.import_module("app.entrypoints.receptor_arranque")
    ReceptorArranqueQt = modulo.ReceptorArranqueQt

    coordinador = _CoordinadorFake()

    def _finalizar(resultado: object) -> None:
        coordinador.finalizar_llamadas.append(resultado)

    coordinador.finalizar_arranque_interfaz = _finalizar
    callbacks_programados: list[object] = []

    def scheduler(callback):
        callbacks_programados.append(callback)

    receptor = ReceptorArranqueQt(coordinador, scheduler=scheduler)
    resultado = object()

    receptor.recibir_ok(resultado)

    assert len(callbacks_programados) == 1
    assert coordinador.finalizar_llamadas == []
    callbacks_programados[0]()
    assert coordinador.finalizar_llamadas == [resultado]
    assert "receptor_delegate_scheduled" in coordinador.stages
    assert "receptor_after_delegate" in coordinador.stages
