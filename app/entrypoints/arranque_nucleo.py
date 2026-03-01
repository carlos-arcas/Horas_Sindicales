from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ResultadoArranque:
    container: Any
    deps_arranque: Any
    idioma: str


def ejecutar_arranque_puro(container_seed: Any, construir_deps_arranque) -> ResultadoArranque:
    resolved_container = container_seed
    if resolved_container is None:
        from app.bootstrap.container import build_container

        try:
            resolved_container = build_container(preferencias_headless=True)
        except TypeError:
            resolved_container = build_container()

    deps_arranque = construir_deps_arranque(resolved_container)
    idioma = deps_arranque.obtener_idioma_ui.ejecutar()
    return ResultadoArranque(
        container=resolved_container,
        deps_arranque=deps_arranque,
        idioma=idioma,
    )
