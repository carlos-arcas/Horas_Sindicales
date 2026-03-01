from __future__ import annotations

import json
from pathlib import Path


class ProveedorDatasetDemo:
    def __init__(self, dataset_path: Path | None = None) -> None:
        self._dataset_path = dataset_path or Path(__file__).resolve().parent / "recursos" / "datos_demo.json"

    def cargar(self) -> dict[str, object]:
        return json.loads(self._dataset_path.read_text(encoding="utf-8"))
