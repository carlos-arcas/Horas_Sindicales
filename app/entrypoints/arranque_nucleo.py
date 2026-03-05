from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ResultadoArranqueCore:
    container: Any


def planificar_arranque_core(container_seed: Any) -> ResultadoArranqueCore:
    resolved_container = container_seed
    if resolved_container is None:
        from app.bootstrap.container import build_container

        try:
            resolved_container = build_container(preferencias_headless=True)
        except TypeError:
            resolved_container = build_container()
    return ResultadoArranqueCore(container=resolved_container)
