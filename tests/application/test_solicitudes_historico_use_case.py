from __future__ import annotations

from app.application.dto import SolicitudDTO
from app.domain.models import Persona


def _persona(nombre: str, *, activa: bool) -> Persona:
    return Persona(
        id=None,
        nombre=nombre,
        genero="F",
        horas_mes_min=600,
        horas_ano_min=7200,
        is_active=activa,
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


def _solicitud(persona_id: int, fecha: str) -> SolicitudDTO:
    return SolicitudDTO(
        id=None,
        persona_id=persona_id,
        fecha_solicitud=fecha,
        fecha_pedida=fecha,
        desde="09:00",
        hasta="10:00",
        completo=False,
        horas=1.0,
        observaciones="hist",
        pdf_path=None,
        pdf_hash=None,
        notas="ok",
    )


def test_listar_historico_incluye_delegadas_inactivas(solicitud_use_cases, persona_repo) -> None:
    activa = persona_repo.create(_persona("Activa", activa=True))
    inactiva = persona_repo.create(_persona("Inactiva", activa=False))

    creada_activa = solicitud_use_cases.crear(_solicitud(int(activa.id or 0), "2025-01-10"))
    creada_inactiva = solicitud_use_cases.crear(_solicitud(int(inactiva.id or 0), "2025-01-11"))
    solicitud_use_cases._repo.mark_generated(int(creada_activa.id or 0), True)
    solicitud_use_cases._repo.mark_generated(int(creada_inactiva.id or 0), True)

    historico = list(solicitud_use_cases.listar_historico())

    assert len(historico) == 2
    assert {sol.persona_id for sol in historico} == {int(activa.id or 0), int(inactiva.id or 0)}
