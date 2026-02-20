from __future__ import annotations

from dataclasses import replace

from app.domain.models import Persona


def _crear_segunda_persona(persona_repo) -> int:
    persona = persona_repo.create(
        Persona(
            id=None,
            nombre="Delegada Dos",
            genero="F",
            horas_mes_min=600,
            horas_ano_min=7200,
            is_active=True,
            cuad_lun_man_min=240,
            cuad_lun_tar_min=240,
            cuad_mar_man_min=240,
            cuad_mar_tar_min=240,
            cuad_mie_man_min=240,
            cuad_mie_tar_min=240,
            cuad_jue_man_min=240,
            cuad_jue_tar_min=240,
            cuad_vie_man_min=240,
            cuad_vie_tar_min=240,
            cuad_sab_man_min=0,
            cuad_sab_tar_min=0,
            cuad_dom_man_min=0,
            cuad_dom_tar_min=0,
        )
    )
    return int(persona.id or 0)


def test_crear_pendiente_y_cambiar_delegada_mantiene_visibilidad_global(
    solicitud_use_cases, persona_repo, solicitud_dto, persona_id: int
) -> None:
    persona_dos_id = _crear_segunda_persona(persona_repo)

    solicitud_use_cases.agregar_solicitud(solicitud_dto)

    pendientes_delegada_dos = list(solicitud_use_cases.listar_pendientes_por_persona(persona_dos_id))
    pendientes_todas = list(solicitud_use_cases.listar_pendientes_all())

    assert pendientes_delegada_dos == []
    assert len(pendientes_todas) == 1
    assert pendientes_todas[0].persona_id == persona_id


def test_crear_pendiente_y_editar_delegada_no_pierde_pendiente(
    solicitud_use_cases, persona_use_cases, solicitud_dto, persona_id: int
) -> None:
    solicitud_use_cases.agregar_solicitud(solicitud_dto)

    persona = persona_use_cases.obtener_persona(persona_id)
    persona_editada = replace(persona, nombre="Delegada Renombrada")
    persona_use_cases.editar_persona(persona_editada)

    pendientes = list(solicitud_use_cases.listar_pendientes_por_persona(persona_id))
    assert len(pendientes) == 1
    assert pendientes[0].id is not None


def test_duplicado_pendiente_ofrece_ir_a_existente(solicitud_use_cases, solicitud_dto) -> None:
    creada, _ = solicitud_use_cases.agregar_solicitud(solicitud_dto)

    duplicate = solicitud_use_cases.buscar_duplicado(solicitud_dto)

    assert duplicate is not None
    assert duplicate.id == creada.id
    assert duplicate.generated is False
