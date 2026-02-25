from __future__ import annotations

from app.domain.models import Persona, Solicitud

def test_crud_insert_update_delete_solicitud(
    solicitud_use_cases,
    solicitud_repo,
    solicitud_dto,
) -> None:
    creada, _ = solicitud_use_cases.agregar_solicitud(solicitud_dto)
    assert creada.id is not None

    solicitud_repo.update_pdf_info(creada.id, "/tmp/solicitud.pdf", "hash-123")
    persistida = solicitud_repo.get_by_id(creada.id)
    assert persistida is not None
    assert persistida.pdf_path == "/tmp/solicitud.pdf"
    assert persistida.pdf_hash == "hash-123"
    assert persistida.generated is True

    solicitud_use_cases.eliminar_solicitud(creada.id)
    assert solicitud_repo.get_by_id(creada.id) is None


def test_mark_generated_actualiza_estado_sin_tocar_pdf(
    solicitud_use_cases,
    solicitud_repo,
    solicitud_dto,
) -> None:
    creada, _ = solicitud_use_cases.agregar_solicitud(solicitud_dto)
    assert creada.id is not None

    solicitud_repo.mark_generated(creada.id, True)

    persistida = solicitud_repo.get_by_id(creada.id)
    assert persistida is not None
    assert persistida.generated is True
    assert persistida.pdf_path is None
    assert persistida.pdf_hash is None


def test_find_duplicate_filtra_por_persona_id(solicitud_repo, persona_repo) -> None:
    primera = persona_repo.create(
        Persona(
            id=None,
            nombre="Delegada Infra A",
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
    segunda = persona_repo.create(
        Persona(
            id=None,
            nombre="Delegada Infra B",
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

    def _sol(persona_id: int) -> Solicitud:
        return Solicitud(
            id=None,
            persona_id=persona_id,
            fecha_solicitud="2025-01-10",
            fecha_pedida="2025-01-20",
            desde_min=540,
            hasta_min=660,
            completo=False,
            horas_solicitadas_min=120,
            observaciones="",
            notas="",
            pdf_path=None,
            pdf_hash=None,
            generated=False,
        )

    creada_a = solicitud_repo.create(_sol(int(primera.id or 0)))
    solicitud_repo.create(_sol(int(segunda.id or 0)))

    duplicate_a = solicitud_repo.find_duplicate(int(primera.id or 0), "2025-01-20", 540, 660, False)
    duplicate_b = solicitud_repo.find_duplicate(int(segunda.id or 0), "2025-01-20", 540, 660, False)

    assert duplicate_a is not None
    assert duplicate_b is not None
    assert duplicate_a.id == creada_a.id
    assert duplicate_a.persona_id != duplicate_b.persona_id
