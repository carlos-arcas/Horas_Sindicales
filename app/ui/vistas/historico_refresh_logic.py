from __future__ import annotations

from collections.abc import Callable

from app.application.dto import PersonaDTO, SolicitudDTO


def build_historico_rows(
    personas: list[PersonaDTO],
    listar_solicitudes_por_persona: Callable[[int], list[SolicitudDTO]],
) -> list[SolicitudDTO]:
    solicitudes: list[SolicitudDTO] = []
    for persona in personas:
        if persona.id is None:
            continue
        solicitudes.extend(listar_solicitudes_por_persona(persona.id))
    return solicitudes
