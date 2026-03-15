from __future__ import annotations

from pathlib import Path

from app.application.dto import SolicitudDTO
from app.application.use_cases import SolicitudUseCases
from app.domain.models import Persona
from app.infrastructure.repos_sqlite import (
    RepositorioPersonasSQLite,
    SolicitudRepositorySQLite,
)
from app.infrastructure.sistema_archivos.local import SistemaArchivosLocal


class FakeGeneradorPdf:
    def __init__(self) -> None:
        self.llamadas_solicitudes: list[tuple[list[SolicitudDTO], Persona, Path]] = []
        self.llamadas_historico: list[tuple[list[SolicitudDTO], Persona, Path, dict[int, Persona] | None]] = []

    def construir_nombre_archivo(
        self, nombre_solicitante: str, fechas: list[str]
    ) -> str:
        _ = (nombre_solicitante, fechas)
        return "fake.pdf"

    def generar_pdf_solicitudes(
        self,
        solicitudes,
        persona,
        destino,
        intro_text=None,
        logo_path=None,
        include_hours_in_horario=None,
    ):
        _ = (intro_text, logo_path, include_hours_in_horario)
        destino.write_bytes(b"%PDF-1.4 fake")
        solicitudes_list = list(solicitudes)
        self.llamadas_solicitudes.append((solicitudes_list, persona, destino))
        return destino

    def generar_pdf_historico(
        self, solicitudes, persona, destino, intro_text=None, logo_path=None, personas_por_id=None
    ):
        _ = (intro_text, logo_path)
        solicitudes_list = list(solicitudes)
        self.llamadas_historico.append((solicitudes_list, persona, destino, personas_por_id))
        destino.write_bytes(b"%PDF-1.4 fake")
        return destino


def test_confirmar_lote_llama_puerto_pdf_con_datos_esperados(
    connection,
    tmp_path: Path,
) -> None:
    persona_repo = RepositorioPersonasSQLite(connection)
    solicitud_repo = SolicitudRepositorySQLite(connection)
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

    fake_pdf = FakeGeneradorPdf()
    use_case = SolicitudUseCases(solicitud_repo, persona_repo, generador_pdf=fake_pdf, fs=SistemaArchivosLocal())
    solicitud = SolicitudDTO(
        id=None,
        persona_id=int(persona.id or 0),
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

    creadas, pendientes, errores, pdf_path = use_case.confirmar_lote_y_generar_pdf(
        [solicitud],
        tmp_path / "solicitud.pdf",
    )

    assert not pendientes
    assert not errores
    assert len(creadas) == 1
    assert pdf_path is not None
    assert len(fake_pdf.llamadas_solicitudes) == 1

    solicitudes_enviadas, persona_enviada, destino = fake_pdf.llamadas_solicitudes[0]
    assert len(solicitudes_enviadas) == 1
    assert solicitudes_enviadas[0].persona_id == solicitud.persona_id
    assert solicitudes_enviadas[0].fecha_pedida == solicitud.fecha_pedida
    assert persona_enviada.id == persona.id
    assert destino == tmp_path / "solicitud.pdf"


def test_confirmar_lote_colision_pdf_renombra_destino_sin_error(
    connection, tmp_path: Path
) -> None:
    persona_repo = RepositorioPersonasSQLite(connection)
    solicitud_repo = SolicitudRepositorySQLite(connection)
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

    fake_pdf = FakeGeneradorPdf()
    use_case = SolicitudUseCases(solicitud_repo, persona_repo, generador_pdf=fake_pdf, fs=SistemaArchivosLocal())
    solicitud = SolicitudDTO(
        id=None,
        persona_id=int(persona.id or 0),
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

    (tmp_path / "solicitud.pdf").write_bytes(b"existing")

    _, _, errores, ruta_pdf = use_case.confirmar_lote_y_generar_pdf(
        [solicitud],
        tmp_path / "solicitud.pdf",
    )

    assert errores == []
    assert ruta_pdf is not None
    assert str(ruta_pdf).endswith("solicitud (1).pdf")


def test_generar_pdf_historico_resuelve_personas_por_fila(connection, tmp_path: Path) -> None:
    persona_repo = RepositorioPersonasSQLite(connection)
    solicitud_repo = SolicitudRepositorySQLite(connection)
    dora = persona_repo.create(
        Persona(
            id=None,
            nombre="Dora Delegada",
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
    lorena = persona_repo.create(
        Persona(
            id=None,
            nombre="Lorena Delegada",
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
    fake_pdf = FakeGeneradorPdf()
    use_case = SolicitudUseCases(solicitud_repo, persona_repo, generador_pdf=fake_pdf, fs=SistemaArchivosLocal())
    solicitudes = [
        SolicitudDTO(
            id=1, persona_id=int(dora.id or 0), fecha_solicitud="2025-02-01", fecha_pedida="2025-02-01",
            desde="09:00", hasta="10:00", completo=False, horas=1.0, observaciones=None, pdf_path=None, pdf_hash=None
        ),
        SolicitudDTO(
            id=2, persona_id=int(lorena.id or 0), fecha_solicitud="2025-02-02", fecha_pedida="2025-02-02",
            desde="11:00", hasta="12:00", completo=False, horas=1.0, observaciones=None, pdf_path=None, pdf_hash=None
        ),
    ]

    use_case.generar_pdf_historico(solicitudes, tmp_path / "historico.pdf")

    assert len(fake_pdf.llamadas_historico) == 1
    _, _, _, personas_por_id = fake_pdf.llamadas_historico[0]
    assert personas_por_id is not None
    assert sorted(persona.nombre for persona in personas_por_id.values()) == ["Dora Delegada", "Lorena Delegada"]
