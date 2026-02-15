from __future__ import annotations

from dataclasses import replace


def test_editar_persona_no_cambia_uuid(persona_repo, persona_use_cases, persona_id: int) -> None:
    uuid_antes = persona_repo.get_or_create_uuid(persona_id)
    persona = persona_use_cases.obtener_persona(persona_id)
    persona_editada = replace(persona, nombre="Delegada Editada")

    persona_use_cases.editar_persona(persona_editada)

    uuid_despues = persona_repo.get_or_create_uuid(persona_id)
    assert uuid_antes == uuid_despues
