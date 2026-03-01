from __future__ import annotations

import json

from app.core.metrics import MetricsRegistry
from app.infrastructure.exportador_metricas import MetricsExporter


def test_exportar_snapshot_crea_archivo_en_logs_con_contenido(tmp_path) -> None:
    registry = MetricsRegistry()
    registry.incrementar("sync_runs")
    registry.registrar_tiempo("sync_ms", 10.0)
    registry.registrar_tiempo("sync_ms", 30.0)
    exporter = MetricsExporter(registry=registry, base_dir=tmp_path)

    destino = exporter.exportar_snapshot()

    assert destino == tmp_path / "logs" / "metrics_snapshot.json"
    assert destino.exists()
    contenido = json.loads(destino.read_text(encoding="utf-8"))
    assert contenido["counters"] == {"sync_runs": 1}
    assert contenido["timings_ms"]["sync_ms"] == {
        "count": 2,
        "last": 30.0,
        "avg": 20.0,
        "max": 30.0,
    }


def test_exportar_snapshot_sobrescribe_snapshot_previo(tmp_path) -> None:
    registry = MetricsRegistry()
    exporter = MetricsExporter(registry=registry, base_dir=tmp_path)

    primer_destino = exporter.exportar_snapshot()
    registry.incrementar("sync_runs", 3)
    segundo_destino = exporter.exportar_snapshot()

    assert primer_destino == segundo_destino
    contenido = json.loads(segundo_destino.read_text(encoding="utf-8"))
    assert contenido["counters"] == {"sync_runs": 3}
