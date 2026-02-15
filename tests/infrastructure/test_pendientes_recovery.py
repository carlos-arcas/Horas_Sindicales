from __future__ import annotations

from app.application.dto import SolicitudDTO
from app.domain.models import Persona


def _build_dto(persona_id: int, fecha: str, desde: str, hasta: str) -> SolicitudDTO:
    return SolicitudDTO(
        id=None,
        persona_id=persona_id,
        fecha_solicitud=fecha,
        fecha_pedida=fecha,
        desde=desde,
        hasta=hasta,
        completo=False,
        horas=2,
        observaciones=None,
        pdf_path=None,
        pdf_hash=None,
        notas=None,
    )


def test_list_pendientes_by_persona_y_all(solicitud_use_cases, solicitud_repo, persona_repo, persona_id: int) -> None:
    persona_dos = persona_repo.create(
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
    persona_dos_id = int(persona_dos.id or 0)

    solicitud_use_cases.agregar_solicitud(_build_dto(persona_id, "2025-01-10", "09:00", "11:00"))
    solicitud_use_cases.agregar_solicitud(_build_dto(persona_dos_id, "2025-01-11", "09:00", "11:00"))

    pendientes_persona_uno = list(solicitud_repo.list_pendientes_by_persona(persona_id))
    pendientes_all = list(solicitud_repo.list_pendientes_all())

    assert len(pendientes_persona_uno) == 1
    assert len(pendientes_all) == 2


def test_list_pendientes_huerfanas(connection, solicitud_repo) -> None:
    connection.execute("PRAGMA foreign_keys = OFF")
    connection.execute(
        """
        INSERT INTO solicitudes (
            uuid, persona_id, fecha_solicitud, fecha_pedida, desde_min, hasta_min, completo,
            horas_solicitadas_min, observaciones, notas, generated, deleted
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "sol-huerfana",
            9999,
            "2025-01-10",
            "2025-01-10",
            540,
            600,
            0,
            60,
            None,
            "huerfana",
            0,
            0,
        ),
    )
    connection.commit()

    huerfanas = list(solicitud_repo.list_pendientes_huerfanas())

    assert len(huerfanas) == 1
    assert huerfanas[0].id is not None
