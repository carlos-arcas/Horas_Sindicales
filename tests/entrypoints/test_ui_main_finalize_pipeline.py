from __future__ import annotations

from app.entrypoints.ui_main import _CoordinadorArranqueConCierreDeterminista


class _CoordinadorPrueba(_CoordinadorArranqueConCierreDeterminista):
    def __init__(self) -> None:
        self.stages: list[str] = []
        self._boot_timeout_disparado = False
        self._boot_finalizado = False
        self.pipeline_llamadas = 0
        self.fallback_llamadas = 0
        self.ultima_etapa = ""

    def _marcar_boot_stage(self, stage: str) -> None:
        self.stages.append(stage)

    def _finalizar_arranque_pipeline(self, startup_payload) -> bool:
        self.pipeline_llamadas += 1
        return True

    def _mostrar_fallback_arranque(self) -> None:
        self.fallback_llamadas += 1


def test_finalizar_arranque_interfaz_ejecuta_pipeline_una_vez_sin_guard_abort() -> None:
    coordinador = _CoordinadorPrueba()

    coordinador.finalizar_arranque_interfaz(object())

    assert coordinador.pipeline_llamadas == 1
    assert coordinador.fallback_llamadas == 0
    assert "finalize_pipeline_begin" in coordinador.stages
    assert "finalize_pipeline_end" in coordinador.stages


def test_finalizar_arranque_interfaz_con_guard_abort_muestra_fallback() -> None:
    coordinador = _CoordinadorPrueba()
    coordinador._boot_finalizado = True

    coordinador.finalizar_arranque_interfaz(object())

    assert coordinador.pipeline_llamadas == 0
    assert coordinador.fallback_llamadas == 1
    assert "finalize_guard_abort" in coordinador.stages
