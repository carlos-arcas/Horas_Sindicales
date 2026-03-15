from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

from app.application.dto import SolicitudDTO
from app.application.use_cases.confirmacion_pdf.coordinador_confirmacion_pdf import (
    CoordinadorConfirmacionPdf,
)
from app.application.use_cases.confirmacion_pdf.pdf_confirmadas_builder import (
    PdfConfirmadasPlan,
)
from app.domain.models import Persona


class _Repo:
    def __init__(self) -> None:
        self.updated: list[tuple[int, str, str | None]] = []

    def update_pdf_info(self, solicitud_id: int, pdf_path: str, pdf_hash: str | None) -> None:
        self.updated.append((solicitud_id, pdf_path, pdf_hash))


class _PersonaRepo:
    def __init__(self, persona: Persona | None) -> None:
        self._persona = persona

    def get_by_id(self, _persona_id: int) -> Persona | None:
        return self._persona


class _ConfigRepo:
    class _Cfg:
        pdf_intro_text = "Intro"
        pdf_logo_path = "logo.png"
        pdf_include_hours_in_horario = True

    def get(self):
        return self._Cfg()


class _Pdf:
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
        return destino


class _Fs:
    def existe_ruta(self, ruta: Path) -> bool:
        _ = ruta
        return False


def _persona() -> Persona:
    return Persona(
        id=1,
        nombre="Delegada",
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


def _solicitud(sid: int | None, persona_id: int = 1) -> SolicitudDTO:
    return SolicitudDTO(
        id=sid,
        persona_id=persona_id,
        fecha_solicitud="2025-01-10",
        fecha_pedida="2025-01-15",
        desde="09:00",
        hasta="11:00",
        completo=False,
        horas=2.0,
        observaciones=None,
        pdf_path=None,
        pdf_hash=None,
        notas=None,
    )


def _coordinador() -> CoordinadorConfirmacionPdf:
    return CoordinadorConfirmacionPdf(
        repo=_Repo(),
        persona_repo=_PersonaRepo(_persona()),
        fs=_Fs(),
        config_repo=_ConfigRepo(),
        generador_pdf=_Pdf(),
        crear_pendiente=lambda solicitud, correlation_id=None: solicitud,
    )


def test_confirmar_pdf_por_filtro_none_incluye_varias_delegadas_directo() -> None:
    coordinador = _coordinador()
    pendientes = [_solicitud(10, persona_id=1), _solicitud(11, persona_id=2)]
    coordinador.confirmar_lote_y_generar_pdf = Mock(
        return_value=(pendientes, [], [], Path("/tmp/mix.pdf"))
    )

    ruta, ids, resumen = coordinador.confirmar_y_generar_pdf_por_filtro(
        filtro_delegada=None,
        pendientes=pendientes,
        destino=Path("/tmp/mix.pdf"),
    )

    assert ruta == Path("/tmp/mix.pdf")
    assert ids == [10, 11]
    assert "Modo: todas" in resumen


def test_confirmar_pdf_por_filtro_delegada_aplica_subset_directo() -> None:
    coordinador = _coordinador()
    pendientes = [_solicitud(12, persona_id=5)]
    coordinador.confirmar_lote_y_generar_pdf = Mock(
        return_value=(pendientes, [], [], Path("/tmp/one.pdf"))
    )

    ruta, ids, _ = coordinador.confirmar_y_generar_pdf_por_filtro(
        filtro_delegada=5,
        pendientes=pendientes,
        destino=Path("/tmp/one.pdf"),
    )

    assert ruta == Path("/tmp/one.pdf")
    assert ids == [12]


def test_confirmar_pdf_por_filtro_sin_pendientes_devuelve_warning_directo() -> None:
    coordinador = _coordinador()

    ruta, ids, resumen = coordinador.confirmar_y_generar_pdf_por_filtro(
        filtro_delegada=None,
        pendientes=[],
        destino=Path("/tmp/none.pdf"),
    )

    assert ruta is None
    assert ids == []
    assert "Sin pendientes" in resumen


def test_orquestador_invoca_builder_y_runner_desde_coordinador(monkeypatch) -> None:
    solicitud = _solicitud(10)
    calls: list[str] = []

    def _fake_builder(entrada):
        calls.append("builder")
        assert entrada.creadas == (solicitud,)
        return PdfConfirmadasPlan(actions=(), reason_code="NO_SOLICITUDES")

    def _fake_runner(plan, **kwargs):
        _ = kwargs
        calls.append("runner")
        assert plan.reason_code == "NO_SOLICITUDES"
        return None, []

    import app.application.use_cases.confirmacion_pdf.coordinador_confirmacion_pdf as coord_module

    monkeypatch.setattr(coord_module, "plan_pdf_confirmadas", _fake_builder)
    monkeypatch.setattr(coord_module, "run_pdf_confirmadas_plan", _fake_runner)

    coordinador = _coordinador()
    path, actualizadas = coordinador._generar_pdf_confirmadas(
        [solicitud],
        Path("/tmp/x.pdf"),
        correlation_id=None,
    )

    assert path is None
    assert actualizadas == [solicitud]
    assert calls == ["builder", "runner"]
