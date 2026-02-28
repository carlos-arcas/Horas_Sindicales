from __future__ import annotations

from pathlib import Path

import pytest

from app.application.dto import SolicitudDTO
from app.application.use_cases.solicitudes.pdf_confirmadas_builder import (
    PdfConfirmadasEntrada,
    plan_pdf_confirmadas,
)
from app.domain.models import Persona


def _persona() -> Persona:
    return Persona(
        id=7,
        nombre="Delegada Demo",
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


def _solicitud(idx: int) -> SolicitudDTO:
    return SolicitudDTO(
        id=idx,
        persona_id=7,
        fecha_solicitud="2025-01-10",
        fecha_pedida=f"2025-01-{10+idx:02d}",
        desde="09:00",
        hasta="10:00",
        completo=False,
        horas=1.0,
        observaciones=None,
        pdf_path=None,
        pdf_hash=None,
    )


@pytest.mark.parametrize(
    ("cantidad", "persona_ok", "generador_ok", "esperado"),
    [
        (0, False, False, "NO_SOLICITUDES"),
        (0, False, True, "NO_SOLICITUDES"),
        (0, True, False, "NO_SOLICITUDES"),
        (0, True, True, "NO_SOLICITUDES"),
        (1, False, False, "PERSONA_NO_ENCONTRADA"),
        (1, False, True, "PERSONA_NO_ENCONTRADA"),
        (1, True, False, "GENERADOR_NO_CONFIGURADO"),
        (1, True, True, "PLAN_READY"),
        (3, False, False, "PERSONA_NO_ENCONTRADA"),
        (3, False, True, "PERSONA_NO_ENCONTRADA"),
        (3, True, False, "GENERADOR_NO_CONFIGURADO"),
        (3, True, True, "PLAN_READY"),
    ],
)
def test_precedencia_reason_code(
    cantidad: int,
    persona_ok: bool,
    generador_ok: bool,
    esperado: str,
) -> None:
    entrada = PdfConfirmadasEntrada(
        creadas=tuple(_solicitud(i) for i in range(cantidad)),
        destino=Path("/tmp/out.pdf"),
        persona=_persona() if persona_ok else None,
        generador_configurado=generador_ok,
        intro_text="Intro",
        logo_path="logo.png",
        include_hours_in_horario=True,
    )

    plan = plan_pdf_confirmadas(entrada)

    assert plan.reason_code == esperado


@pytest.mark.parametrize(
    ("cantidad", "persona", "generador", "esperado"),
    [
        (0, None, False, "NO_SOLICITUDES"),
        (1, None, True, "PERSONA_NO_ENCONTRADA"),
        (1, _persona(), False, "GENERADOR_NO_CONFIGURADO"),
        (1, _persona(), True, "PLAN_READY"),
        (2, _persona(), True, "PLAN_READY"),
    ],
)
def test_reason_code_exacto_en_casos_clave(cantidad: int, persona: Persona | None, generador: bool, esperado: str) -> None:
    entrada = PdfConfirmadasEntrada(
        creadas=tuple(_solicitud(i) for i in range(cantidad)),
        destino=Path("/tmp/out.pdf"),
        persona=persona,
        generador_configurado=generador,
        intro_text=None,
        logo_path=None,
        include_hours_in_horario=None,
    )
    assert plan_pdf_confirmadas(entrada).reason_code == esperado


@pytest.mark.parametrize("cantidad", [1, 2, 3, 4, 5, 8])
def test_orden_estable_de_acciones(cantidad: int) -> None:
    creadas = tuple(_solicitud(i) for i in range(cantidad))
    plan = plan_pdf_confirmadas(
        PdfConfirmadasEntrada(
            creadas=creadas,
            destino=Path("/tmp/out.pdf"),
            persona=_persona(),
            generador_configurado=True,
            intro_text="Intro",
            logo_path="logo.png",
            include_hours_in_horario=False,
        )
    )

    action_types = [a.action_type for a in plan.actions]
    assert action_types[:2] == ["GENERATE_PDF", "HASH_FILE"]
    assert action_types[2:] == ["UPDATE_STATUS"] * cantidad
    assert [a.solicitud.id for a in plan.actions[2:]] == [s.id for s in creadas]


@pytest.mark.parametrize(
    ("intro", "logo", "include_hours"),
    [
        (None, None, None),
        ("Intro", None, None),
        ("Intro", "logo.png", None),
        ("Intro", "logo.png", True),
        ("Intro", "logo.png", False),
    ],
)
def test_payload_contractual_sin_io(intro: str | None, logo: str | None, include_hours: bool | None) -> None:
    creadas = (_solicitud(1), _solicitud(2))
    destino = Path("/tmp/out.pdf")
    persona = _persona()

    plan = plan_pdf_confirmadas(
        PdfConfirmadasEntrada(
            creadas=creadas,
            destino=destino,
            persona=persona,
            generador_configurado=True,
            intro_text=intro,
            logo_path=logo,
            include_hours_in_horario=include_hours,
        )
    )

    action = plan.actions[0]
    assert action.action_type == "GENERATE_PDF"
    assert action.solicitudes == creadas
    assert action.destino == destino
    assert action.persona == persona
    assert action.intro_text == intro
    assert action.logo_path == logo
    assert action.include_hours_in_horario == include_hours
