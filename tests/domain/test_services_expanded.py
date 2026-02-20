from __future__ import annotations

from dataclasses import replace

import pytest

from app.domain.models import Persona, SheetsConfig, Solicitud
from app.domain.services import ValidacionError, validar_persona, validar_sheets_config, validar_solicitud


def _valid_persona() -> Persona:
    return Persona(
        id=1,
        nombre="Ana",
        genero="F",
        horas_mes_min=600,
        horas_ano_min=7200,
        is_active=True,
        cuad_lun_man_min=60,
        cuad_lun_tar_min=60,
        cuad_mar_man_min=60,
        cuad_mar_tar_min=60,
        cuad_mie_man_min=60,
        cuad_mie_tar_min=60,
        cuad_jue_man_min=60,
        cuad_jue_tar_min=60,
        cuad_vie_man_min=60,
        cuad_vie_tar_min=60,
        cuad_sab_man_min=0,
        cuad_sab_tar_min=0,
        cuad_dom_man_min=0,
        cuad_dom_tar_min=0,
    )


@pytest.mark.parametrize("field", ["horas_mes_min", "cuad_lun_man_min", "cuad_dom_tar_min"])
def test_validar_persona_rejects_negative_numeric_fields(field: str) -> None:
    persona = replace(_valid_persona(), **{field: -1})
    with pytest.raises(ValidacionError):
        validar_persona(persona)


def test_validar_solicitud_rejects_invalid_payload() -> None:
    with pytest.raises(ValidacionError):
        validar_solicitud(
            Solicitud(
                id=1,
                persona_id=0,
                fecha_solicitud="",
                fecha_pedida="",
                desde_min=None,
                hasta_min=None,
                completo=True,
                horas_solicitadas_min=0,
                observaciones="",
                notas="",
                pdf_path=None,
                pdf_hash=None,
                generated=False,
            )
        )


@pytest.mark.parametrize(
    ("spreadsheet_id", "credentials_path"),
    [("", "cred.json"), ("sheet", "")],
)
def test_validar_sheets_config_requires_non_empty_fields(spreadsheet_id: str, credentials_path: str) -> None:
    with pytest.raises(ValidacionError):
        validar_sheets_config(
            SheetsConfig(
                spreadsheet_id=spreadsheet_id,
                credentials_path=credentials_path,
                device_id="dev-1",
            )
        )
