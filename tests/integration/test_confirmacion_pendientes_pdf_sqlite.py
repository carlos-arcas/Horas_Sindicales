from __future__ import annotations

from pathlib import Path

from app.application.dto import SolicitudDTO
from app.application.use_cases import SolicitudUseCases
from app.application.use_cases.confirmacion_pdf.caso_uso import ConfirmarPendientesPdfCasoUso
from app.application.use_cases.confirmacion_pdf.modelos import SolicitudConfirmarPdfPeticion
from app.application.use_cases.solicitudes.crear_pendiente_caso_uso import (
    CrearPendienteCasoUso,
    SolicitudCrearPendientePeticion,
)
from app.domain.models import Persona
from app.infrastructure.confirmacion_pdf.adaptadores import RepositorioSolicitudesDesdeCasosUso


class SistemaArchivosFake:
    def mkdir(self, path: Path, parents: bool = False, exist_ok: bool = False) -> None:
        path.mkdir(parents=parents, exist_ok=exist_ok)

    def existe(self, path: Path) -> bool:
        return path.exists()


class GeneradorPdfFake:
    def generar_pdf_solicitudes(self, solicitudes, persona, destino, **kwargs):
        destino.write_text("%PDF-fake", encoding="utf-8")
        return destino


def _crear_persona(persona_repo) -> int:
    persona = persona_repo.create(
        Persona(
            id=None,
            nombre="Delegada Integracion",
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
    return int(persona.id)


def _solicitud(persona_id: int, fecha: str, desde: str = "09:00", hasta: str = "10:00") -> SolicitudDTO:
    return SolicitudDTO(
        id=None,
        persona_id=persona_id,
        fecha_solicitud="2026-01-01",
        fecha_pedida=fecha,
        desde=desde,
        hasta=hasta,
        completo=False,
        horas=1.0,
        observaciones="obs",
        pdf_path=None,
        pdf_hash=None,
        notas="nota",
    )


def _crear_caso_confirmacion(solicitud_repo, persona_repo) -> ConfirmarPendientesPdfCasoUso:
    solicitudes_uc = SolicitudUseCases(
        solicitud_repo,
        persona_repo,
        generador_pdf=GeneradorPdfFake(),
        fs=SistemaArchivosFake(),
    )
    return ConfirmarPendientesPdfCasoUso(
        repositorio=RepositorioSolicitudesDesdeCasosUso(solicitudes_uc),
        sistema_archivos=SistemaArchivosFake(),
    )


def test_crear_pendiente_y_listar_pendientes_sqlite(connection, solicitud_repo, persona_repo) -> None:
    persona_id = _crear_persona(persona_repo)
    solicitudes_uc = SolicitudUseCases(solicitud_repo, persona_repo)

    creada, _saldos = solicitudes_uc.agregar_solicitud(_solicitud(persona_id, "2026-01-10"))

    pendientes = list(solicitudes_uc.listar_pendientes_all())

    assert creada.id is not None
    assert any(item.id == creada.id for item in pendientes)


def test_regresion_crear_pendiente_retorna_ids_para_refresco_tabla(connection, solicitud_repo, persona_repo) -> None:
    persona_id = _crear_persona(persona_repo)
    solicitudes_uc = SolicitudUseCases(solicitud_repo, persona_repo)
    adapter = RepositorioSolicitudesDesdeCasosUso(solicitudes_uc)
    caso = CrearPendienteCasoUso(repositorio=adapter)

    resultado = caso.execute(
        SolicitudCrearPendientePeticion(
            solicitud=_solicitud(persona_id, "2026-01-15"),
            correlation_id="corr-crear-pendiente",
        )
    )

    ids_reales = [item.id for item in solicitudes_uc.listar_pendientes_all() if item.id is not None]
    assert resultado.solicitud_id is not None
    assert resultado.solicitud_id in resultado.pendientes_ids
    assert resultado.pendientes_ids == ids_reales


def test_confirmar_sin_pdf_actualiza_pendientes_restantes(connection, solicitud_repo, persona_repo) -> None:
    persona_id = _crear_persona(persona_repo)
    solicitudes_uc = SolicitudUseCases(solicitud_repo, persona_repo)
    primera, _ = solicitudes_uc.agregar_solicitud(_solicitud(persona_id, "2026-01-10"))
    segunda, _ = solicitudes_uc.agregar_solicitud(_solicitud(persona_id, "2026-01-11"))

    caso = _crear_caso_confirmacion(solicitud_repo, persona_repo)
    resultado = caso.execute(
        SolicitudConfirmarPdfPeticion(
            pendientes_ids=[int(primera.id or 0)],
            generar_pdf=False,
            correlation_id="corr-sin-pdf",
        )
    )

    pendientes_restantes = list(SolicitudUseCases(solicitud_repo, persona_repo).listar_pendientes_all())

    assert resultado.confirmadas_ids == [primera.id]
    assert resultado.errores == []
    assert resultado.pendientes_restantes == [segunda.id]
    assert [item.id for item in pendientes_restantes] == [segunda.id]


def test_confirmar_con_pdf_confirma_y_devuelve_ruta_pdf(connection, solicitud_repo, persona_repo, tmp_path) -> None:
    persona_id = _crear_persona(persona_repo)
    solicitudes_uc = SolicitudUseCases(solicitud_repo, persona_repo)
    primera, _ = solicitudes_uc.agregar_solicitud(_solicitud(persona_id, "2026-01-10"))
    segunda, _ = solicitudes_uc.agregar_solicitud(_solicitud(persona_id, "2026-01-11"))

    caso = _crear_caso_confirmacion(solicitud_repo, persona_repo)
    ruta_pdf = tmp_path / "confirmadas.pdf"
    resultado = caso.execute(
        SolicitudConfirmarPdfPeticion(
            pendientes_ids=[int(primera.id or 0)],
            generar_pdf=True,
            destino_pdf=ruta_pdf,
            correlation_id="corr-con-pdf",
        )
    )

    pendientes_restantes = list(SolicitudUseCases(solicitud_repo, persona_repo).listar_pendientes_all())

    assert resultado.ruta_pdf == ruta_pdf
    assert ruta_pdf.exists()
    assert resultado.confirmadas_ids == [primera.id]
    assert resultado.errores == []
    assert resultado.pendientes_restantes == [segunda.id]
    assert [item.id for item in pendientes_restantes] == [segunda.id]
