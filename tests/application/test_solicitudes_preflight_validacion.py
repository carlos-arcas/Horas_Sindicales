from __future__ import annotations

from pathlib import Path

import pytest

from app.application.dto import SolicitudDTO
from app.application.use_cases import SolicitudUseCases
from app.application.use_cases.solicitudes.validaciones import validar_solicitud_dto_declarativo
from app.domain.models import Persona
from app.domain.services import BusinessRuleError, ValidacionError
from app.infrastructure.repos_sqlite import PersonaRepositorySQLite, SolicitudRepositorySQLite


class FakeGeneradorPdf:
    def construir_nombre_archivo(self, nombre_solicitante: str, fechas: list[str]) -> str:
        _ = (nombre_solicitante, fechas)
        return "salida.pdf"

    def generar_pdf_solicitudes(
        self,
        solicitudes,
        persona,
        destino,
        intro_text=None,
        logo_path=None,
        include_hours_in_horario=None,
    ):
        _ = (solicitudes, persona, intro_text, logo_path, include_hours_in_horario)
        destino.write_bytes(b"%PDF-1.4 fake")
        return destino

    def generar_pdf_historico(self, solicitudes, persona, destino, intro_text=None, logo_path=None):
        _ = (solicitudes, persona, intro_text, logo_path)
        destino.write_bytes(b"%PDF-1.4 fake")
        return destino


def _crear_persona(persona_repo: PersonaRepositorySQLite) -> int:
    persona = persona_repo.create(
        Persona(
            id=None,
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
    )
    return int(persona.id or 0)


def _solicitud(persona_id: int) -> SolicitudDTO:
    return SolicitudDTO(
        id=None,
        persona_id=persona_id,
        fecha_solicitud="2025-01-10",
        fecha_pedida="2025-01-15",
        desde="09:00",
        hasta="11:00",
        completo=False,
        horas=2.0,
        observaciones="Obs",
        pdf_path=None,
        pdf_hash=None,
        notas="Nota",
    )


def test_validacion_declarativa_rechaza_intervalo_invalido() -> None:
    dto = SolicitudDTO(
        id=None,
        persona_id=1,
        fecha_solicitud="2025-01-10",
        fecha_pedida="2025-01-15",
        desde="11:00",
        hasta="09:00",
        completo=False,
        horas=2.0,
        observaciones=None,
        pdf_path=None,
        pdf_hash=None,
    )

    with pytest.raises(ValidacionError, match="hasta"):
        validar_solicitud_dto_declarativo(dto)


def test_confirmar_lote_preflight_resuelve_colision_si_pdf_ya_existe(connection, tmp_path: Path) -> None:
    persona_repo = PersonaRepositorySQLite(connection)
    solicitud_repo = SolicitudRepositorySQLite(connection)
    persona_id = _crear_persona(persona_repo)
    use_case = SolicitudUseCases(solicitud_repo, persona_repo, generador_pdf=FakeGeneradorPdf())

    destino = tmp_path / "duplicado.pdf"
    destino.write_bytes(b"contenido previo")

    _creadas, _pendientes, _errores, pdf_path = use_case.confirmar_lote_y_generar_pdf([_solicitud(persona_id)], destino)

    assert pdf_path == tmp_path / "duplicado(1).pdf"


class FakeGeneradorPdfFalla(FakeGeneradorPdf):
    def generar_pdf_solicitudes(
        self,
        solicitudes,
        persona,
        destino,
        intro_text=None,
        logo_path=None,
        include_hours_in_horario=None,
    ):
        from app.core.errors import InfraError

        raise InfraError("fallo forzado")


def test_confirmar_lote_error_pdf_incluye_incident_id(connection, tmp_path: Path) -> None:
    persona_repo = PersonaRepositorySQLite(connection)
    solicitud_repo = SolicitudRepositorySQLite(connection)
    persona_id = _crear_persona(persona_repo)
    use_case = SolicitudUseCases(solicitud_repo, persona_repo, generador_pdf=FakeGeneradorPdfFalla())

    with pytest.raises(BusinessRuleError, match=r"ID de incidente: INC-"):
        use_case.confirmar_lote_y_generar_pdf([_solicitud(persona_id)], tmp_path / "falla.pdf")
