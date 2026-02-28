from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PersonaOption:
    """Representa una persona de forma agnóstica a Qt.

    Se usa para separar la construcción de reglas de presentación
    de los widgets concretos de la vista.
    """

    id: int | None
    nombre: str


@dataclass(frozen=True)
class PersonasLoadInput:
    """Entrada para calcular el estado de combos relacionados con personas."""

    personas: tuple[PersonaOption, ...]
    select_id: int | None
    saved_delegada_id: object


@dataclass(frozen=True)
class PersonasLoadOutput:
    """Salida lista para ser aplicada por la Thin View en widgets Qt."""

    persona_items: tuple[PersonaOption, ...]
    selected_persona_id: int | None
    persona_nombres: dict[int, str]
    historico_items: tuple[tuple[str, int | None], ...]
    config_items: tuple[tuple[str, int], ...]
    active_config_id: int | None


def resolve_active_delegada_id(delegada_ids: list[int], preferred_id: object) -> int | None:
    """Devuelve la delegada activa válida a partir del id preferido y la lista cargada."""
    if not delegada_ids:
        return None
    preferred_as_text = str(preferred_id)
    for delegada_id in delegada_ids:
        if str(delegada_id) == preferred_as_text:
            return delegada_id
    return delegada_ids[0]


def build_personas_load_output(entrada: PersonasLoadInput) -> PersonasLoadOutput:
    """Calcula listas y selección activa para combos de personas.

    Reglas clave:
    - Respetar orden de carga para el combo principal.
    - Ordenar alfabéticamente (sin distinguir mayúsculas) histórico/config.
    - Si no hay selección explícita válida, usar primer elemento disponible.
    """

    persona_items = entrada.personas
    persona_ids = [persona.id for persona in persona_items]

    selected_persona_id = _resolve_selected_persona_id(persona_ids, entrada.select_id)
    persona_nombres = {int(persona.id): persona.nombre for persona in persona_items if persona.id is not None}

    sorted_personas = tuple(sorted(persona_nombres.items(), key=lambda item: item[1].lower()))
    historico_items = (("Todas", None),) + tuple((nombre, persona_id) for persona_id, nombre in sorted_personas)
    config_items = tuple((nombre, persona_id) for persona_id, nombre in sorted_personas)

    preferred_id = entrada.select_id if entrada.select_id is not None else entrada.saved_delegada_id
    active_config_id = resolve_active_delegada_id([persona_id for persona_id, _ in sorted_personas], preferred_id)

    return PersonasLoadOutput(
        persona_items=persona_items,
        selected_persona_id=selected_persona_id,
        persona_nombres=persona_nombres,
        historico_items=historico_items,
        config_items=config_items,
        active_config_id=active_config_id,
    )


def _resolve_selected_persona_id(persona_ids: list[int | None], select_id: int | None) -> int | None:
    if not persona_ids:
        return None
    if select_id in persona_ids:
        return select_id
    return persona_ids[0]
