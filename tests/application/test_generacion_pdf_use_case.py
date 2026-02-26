from __future__ import annotations

from pathlib import Path

from app.application.dto import SolicitudDTO
from app.application.use_cases import SolicitudUseCases
from app.domain.models import Persona
from app.infrastructure.repos_sqlite import PersonaRepositorySQLite, SolicitudRepositorySQLite


class FakeGeneradorPdf:
    def __init__(self) -> None:
        self.llamadas_solicitudes: list[tuple[list[SolicitudDTO], Persona, Path]] = []

    def construir_nombre_archivo(self, nombre_solicitante: str, fechas: list[str]) -> str:
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

    def generar_pdf_historico(self, solicitudes, persona, destino, intro_text=None, logo_path=None):
        _ = (solicitudes, persona, intro_text, logo_path)
        destino.write_bytes(b"%PDF-1.4 fake")
        return destino


def test_confirmar_lote_llama_puerto_pdf_con_datos_esperados(
    connection,
    tmp_path: Path,
) -> None:
    persona_repo = PersonaRepositorySQLite(connection)
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
    use_case = SolicitudUseCases(solicitud_repo, persona_repo, generador_pdf=fake_pdf)
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


def test_confirmar_pdf_por_filtro_none_incluye_varias_delegadas(connection, tmp_path: Path) -> None:
    persona_repo = PersonaRepositorySQLite(connection)
    solicitud_repo = SolicitudRepositorySQLite(connection)
    p1 = persona_repo.create(Persona(id=None,nombre="A",genero="F",horas_mes_min=600,horas_ano_min=7200,is_active=True,cuad_lun_man_min=240,cuad_lun_tar_min=240,cuad_mar_man_min=240,cuad_mar_tar_min=240,cuad_mie_man_min=240,cuad_mie_tar_min=240,cuad_jue_man_min=240,cuad_jue_tar_min=240,cuad_vie_man_min=240,cuad_vie_tar_min=240,cuad_sab_man_min=0,cuad_sab_tar_min=0,cuad_dom_man_min=0,cuad_dom_tar_min=0))
    p2 = persona_repo.create(Persona(id=None,nombre="B",genero="F",horas_mes_min=600,horas_ano_min=7200,is_active=True,cuad_lun_man_min=240,cuad_lun_tar_min=240,cuad_mar_man_min=240,cuad_mar_tar_min=240,cuad_mie_man_min=240,cuad_mie_tar_min=240,cuad_jue_man_min=240,cuad_jue_tar_min=240,cuad_vie_man_min=240,cuad_vie_tar_min=240,cuad_sab_man_min=0,cuad_sab_tar_min=0,cuad_dom_man_min=0,cuad_dom_tar_min=0))
    fake_pdf = FakeGeneradorPdf()
    use_case = SolicitudUseCases(solicitud_repo, persona_repo, generador_pdf=fake_pdf)
    s1 = SolicitudDTO(id=None, persona_id=int(p1.id or 0), fecha_solicitud="2025-01-10", fecha_pedida="2025-01-15", desde="09:00", hasta="11:00", completo=False, horas=2.0, observaciones=None, pdf_path=None, pdf_hash=None, notas=None)
    s2 = SolicitudDTO(id=None, persona_id=int(p2.id or 0), fecha_solicitud="2025-01-10", fecha_pedida="2025-01-15", desde="11:00", hasta="12:00", completo=False, horas=1.0, observaciones=None, pdf_path=None, pdf_hash=None, notas=None)
    ruta, ids, resumen = use_case.confirmar_y_generar_pdf_por_filtro(filtro_delegada=None, pendientes=[s1, s2], destino=tmp_path / "mix.pdf")
    assert ruta is not None
    assert len(ids) == 2
    assert "Modo: todas" in resumen


def test_confirmar_pdf_por_filtro_delegada_aplica_subset(connection, tmp_path: Path) -> None:
    persona_repo = PersonaRepositorySQLite(connection)
    solicitud_repo = SolicitudRepositorySQLite(connection)
    persona = persona_repo.create(Persona(id=None,nombre="A",genero="F",horas_mes_min=600,horas_ano_min=7200,is_active=True,cuad_lun_man_min=240,cuad_lun_tar_min=240,cuad_mar_man_min=240,cuad_mar_tar_min=240,cuad_mie_man_min=240,cuad_mie_tar_min=240,cuad_jue_man_min=240,cuad_jue_tar_min=240,cuad_vie_man_min=240,cuad_vie_tar_min=240,cuad_sab_man_min=0,cuad_sab_tar_min=0,cuad_dom_man_min=0,cuad_dom_tar_min=0))
    fake_pdf = FakeGeneradorPdf()
    use_case = SolicitudUseCases(solicitud_repo, persona_repo, generador_pdf=fake_pdf)
    s1 = SolicitudDTO(id=None, persona_id=int(persona.id or 0), fecha_solicitud="2025-01-10", fecha_pedida="2025-01-15", desde="09:00", hasta="11:00", completo=False, horas=2.0, observaciones=None, pdf_path=None, pdf_hash=None, notas=None)
    ruta, ids, _ = use_case.confirmar_y_generar_pdf_por_filtro(filtro_delegada=int(persona.id or 0), pendientes=[s1], destino=tmp_path / "one.pdf")
    assert ruta is not None
    assert len(ids) == 1


def test_confirmar_pdf_por_filtro_sin_pendientes_devuelve_warning(connection, tmp_path: Path) -> None:
    persona_repo = PersonaRepositorySQLite(connection)
    solicitud_repo = SolicitudRepositorySQLite(connection)
    fake_pdf = FakeGeneradorPdf()
    use_case = SolicitudUseCases(solicitud_repo, persona_repo, generador_pdf=fake_pdf)
    ruta, ids, resumen = use_case.confirmar_y_generar_pdf_por_filtro(filtro_delegada=None, pendientes=[], destino=tmp_path / "none.pdf")
    assert ruta is None
    assert ids == []
    assert "Sin pendientes" in resumen
