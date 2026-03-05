from __future__ import annotations

import importlib
import sys
from types import SimpleNamespace


class _CoordinadorFake:
    def __init__(self) -> None:
        self.stages: list[str] = []
        self.fallback_llamado = 0

    def _marcar_boot_stage(self, stage: str) -> None:
        self.stages.append(stage)

    def _on_finished_ui(self, _resultado: object) -> None:
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
    receptor = ReceptorArranqueQt(coordinador)

    receptor.recibir_ok(object())

    assert "on_finished_enter_ui" in coordinador.stages
    assert "on_finished_exception_ui" in coordinador.stages
    assert coordinador.fallback_llamado == 1
