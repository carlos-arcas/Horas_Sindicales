from __future__ import annotations

from typing import Any

from app.application.use_cases.sync_sheets import payloads_puros


# Regla pura de resolución para desacoplar la decisión de la ejecución SQL.
def build_persona_resolution_plan(
    persona_uuid: str | None,
    nombre: str,
    by_uuid: dict[str, Any] | None,
    by_nombre: dict[str, Any] | None,
) -> dict[str, Any]:
    return payloads_puros.resolver_persona_accion(persona_uuid, nombre, by_uuid, by_nombre)
