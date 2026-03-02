from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from app.application.dto import SolicitudDTO
from app.application.use_cases import SolicitudUseCases
from app.application.use_cases.solicitudes import use_case as use_case_module
from app.application.use_cases.solicitudes.validaciones import validar_solicitud_dto_declarativo
from app.domain.models import Persona
from app.domain.services import BusinessRuleError, ValidacionError
from app.infrastructure.sistema_archivos.local import SistemaArchivosLocal
from app.infrastructure.repos_sqlite import RepositorioPersonasSQLite, SolicitudRepositorySQLite


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


def _crear_persona(persona_repo: RepositorioPersonasSQLite) -> int:
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


def test_confirmar_lote_preflight_colision_se_resuelve_con_ruta_alternativa(connection, tmp_path: Path) -> None:
    persona_repo = RepositorioPersonasSQLite(connection)
    solicitud_repo = SolicitudRepositorySQLite(connection)
    persona_id = _crear_persona(persona_repo)
    use_case = SolicitudUseCases(solicitud_repo, persona_repo, generador_pdf=FakeGeneradorPdf())

    destino = tmp_path / "duplicado.pdf"
    destino.write_bytes(b"contenido previo")

    _, _, errores, ruta_pdf = use_case.confirmar_lote_y_generar_pdf([_solicitud(persona_id)], destino)

    assert errores == []
    assert ruta_pdf is not None
    assert str(ruta_pdf).endswith("duplicado (1).pdf")
    pdfs_generados = sorted(path.name for path in tmp_path.glob("*.pdf"))
    assert pdfs_generados == ["duplicado (1).pdf", "duplicado.pdf"]


def test_confirmar_lote_resuelve_destino_pdf_una_sola_vez(connection, tmp_path: Path) -> None:
    persona_repo = RepositorioPersonasSQLite(connection)
    solicitud_repo = SolicitudRepositorySQLite(connection)
    persona_id = _crear_persona(persona_repo)
    use_case = SolicitudUseCases(
        solicitud_repo,
        persona_repo,
        generador_pdf=FakeGeneradorPdf(),
        fs=SistemaArchivosLocal(),
    )

    destino = tmp_path / "duplicado.pdf"
    destino.write_bytes(b"contenido previo")

    with (
        patch.object(use_case, "resolver_destino_pdf", wraps=use_case.resolver_destino_pdf) as spy_use_case,
        patch.object(
            use_case_module,
            "resolver_ruta_sin_colision",
            wraps=use_case_module.resolver_ruta_sin_colision,
        ) as spy_policy,
    ):
        _, _, errores, ruta_pdf = use_case.confirmar_lote_y_generar_pdf([_solicitud(persona_id)], destino)

    assert errores == []
    assert ruta_pdf is not None
    assert str(ruta_pdf).endswith("duplicado (1).pdf")
    assert spy_use_case.call_count == 1
    assert spy_policy.call_count == 1


def test_confirmar_lote_no_lanza_error_por_colision_de_ruta(connection, tmp_path: Path) -> None:
    persona_repo = RepositorioPersonasSQLite(connection)
    solicitud_repo = SolicitudRepositorySQLite(connection)
    persona_id = _crear_persona(persona_repo)
    use_case = SolicitudUseCases(solicitud_repo, persona_repo, generador_pdf=FakeGeneradorPdf())

    destino = tmp_path / "colision.pdf"
    destino.write_bytes(b"contenido previo")

    try:
        _, _, errores, ruta_pdf = use_case.confirmar_lote_y_generar_pdf([_solicitud(persona_id)], destino)
    except BusinessRuleError as exc:  # pragma: no cover - regresion
        pytest.fail(f"No debe lanzar BusinessRuleError por colisión: {exc}")

    assert errores == []
    assert ruta_pdf == (tmp_path / "colision (1).pdf").resolve(strict=False)


def test_confirmar_lote_preflight_colision_si_existen_base_y_1_devuelve_2(connection, tmp_path: Path) -> None:
    persona_repo = RepositorioPersonasSQLite(connection)
    solicitud_repo = SolicitudRepositorySQLite(connection)
    persona_id = _crear_persona(persona_repo)
    use_case = SolicitudUseCases(solicitud_repo, persona_repo, generador_pdf=FakeGeneradorPdf())

    (tmp_path / "duplicado.pdf").write_bytes(b"base")
    (tmp_path / "duplicado (1).pdf").write_bytes(b"alternativa 1")

    _, _, errores, ruta_pdf = use_case.confirmar_lote_y_generar_pdf(
        [_solicitud(persona_id)],
        tmp_path / "duplicado.pdf",
    )

    assert errores == []
    assert ruta_pdf is not None
    assert str(ruta_pdf).endswith("duplicado (2).pdf")


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
    persona_repo = RepositorioPersonasSQLite(connection)
    solicitud_repo = SolicitudRepositorySQLite(connection)
    persona_id = _crear_persona(persona_repo)
    use_case = SolicitudUseCases(solicitud_repo, persona_repo, generador_pdf=FakeGeneradorPdfFalla())

    with pytest.raises(BusinessRuleError, match=r"ID de incidente: INC-"):
        use_case.confirmar_lote_y_generar_pdf([_solicitud(persona_id)], tmp_path / "falla.pdf")
