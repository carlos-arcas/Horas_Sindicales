from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol


class _MetricsRegistryProtocol(Protocol):
    def snapshot(self) -> dict[str, dict[str, object]]:
        ...


class MetricsExporter:
    def __init__(self, registry: _MetricsRegistryProtocol, base_dir: Path | str) -> None:
        self._registry = registry
        self._base_dir = Path(base_dir)

    def exportar_snapshot(self) -> Path:
        destino = self._base_dir / "logs" / "metrics_snapshot.json"
        destino.parent.mkdir(parents=True, exist_ok=True)
        contenido = self._registry.snapshot()
        destino.write_text(
            json.dumps(contenido, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        return destino
