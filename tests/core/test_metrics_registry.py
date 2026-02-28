from __future__ import annotations

from threading import Thread
from time import sleep

from app.core import metrics


def test_incrementar_contador() -> None:
    registry = metrics.MetricsRegistry()

    registry.incrementar("solicitudes_creadas")
    registry.incrementar("solicitudes_creadas", 2)

    assert registry.contador("solicitudes_creadas") == 3


def test_registrar_latencia() -> None:
    registry = metrics.MetricsRegistry()

    registry.registrar_tiempo("latency.generar_pdf_ms", 12.5)

    snapshot = registry.snapshot()
    assert snapshot["timings_ms"]["latency.generar_pdf_ms"]["count"] == 1
    assert snapshot["timings_ms"]["latency.generar_pdf_ms"]["last"] == 12.5


def test_decorator_mide_tiempo_real() -> None:
    original_registry = metrics.metrics_registry
    metrics.metrics_registry = metrics.MetricsRegistry()

    @metrics.medir_tiempo("latency.decorator_ms")
    def _operacion() -> str:
        sleep(0.01)
        return "ok"

    try:
        result = _operacion()
        measured = metrics.metrics_registry.snapshot()["timings_ms"]["latency.decorator_ms"]["last"]
    finally:
        metrics.metrics_registry = original_registry

    assert result == "ok"
    assert measured > 0


def test_snapshot_devuelve_datos_coherentes() -> None:
    registry = metrics.MetricsRegistry()

    registry.incrementar("syncs_ejecutados")
    registry.registrar_tiempo("latency.sync_bidireccional_ms", 10)
    registry.registrar_tiempo("latency.sync_bidireccional_ms", 30)

    snapshot = registry.snapshot()

    assert snapshot["counters"]["syncs_ejecutados"] == 1
    assert snapshot["timings_ms"]["latency.sync_bidireccional_ms"]["count"] == 2
    assert snapshot["timings_ms"]["latency.sync_bidireccional_ms"]["avg"] == 20
    assert snapshot["timings_ms"]["latency.sync_bidireccional_ms"]["max"] == 30


def test_thread_safety_basica() -> None:
    registry = metrics.MetricsRegistry()

    def _worker() -> None:
        for _ in range(200):
            registry.incrementar("conflictos_detectados")
            registry.registrar_tiempo("latency.confirmar_solicitudes_ms", 1.0)

    threads = [Thread(target=_worker) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    snapshot = registry.snapshot()
    assert snapshot["counters"]["conflictos_detectados"] == 1600
    assert snapshot["timings_ms"]["latency.confirmar_solicitudes_ms"]["count"] == 1600
