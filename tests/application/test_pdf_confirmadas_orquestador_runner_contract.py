from __future__ import annotations

from pathlib import Path

import pytest

from app.application.dto import SolicitudDTO
from app.application.use_cases import SolicitudUseCases
from app.application.use_cases.solicitudes.pdf_confirmadas_builder import PdfAction, PdfConfirmadasPlan
from app.application.use_cases.solicitudes.pdf_confirmadas_runner import run_pdf_confirmadas_plan
from app.core.errors import InfraError
from app.domain.models import Persona
from app.domain.services import BusinessRuleError


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
    def __init__(self) -> None:
        self.calls: list[str] = []

    def generar_pdf_solicitudes(self, solicitudes, persona, destino, intro_text=None, logo_path=None, include_hours_in_horario=None):
        _ = (solicitudes, persona, intro_text, logo_path, include_hours_in_horario)
        self.calls.append("GENERATE_PDF")
        return destino


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


def _solicitud(sid: int | None = 10) -> SolicitudDTO:
    return SolicitudDTO(
        id=sid,
        persona_id=1,
        fecha_solicitud="2025-01-01",
        fecha_pedida="2025-01-10",
        desde="09:00",
        hasta="10:00",
        completo=False,
        horas=1.0,
        observaciones=None,
        pdf_path=None,
        pdf_hash=None,
    )


def test_runner_ejecuta_acciones_en_orden() -> None:
    repo = _Repo()
    pdf = _Pdf()
    solicitud = _solicitud(11)
    order: list[str] = []

    plan = PdfConfirmadasPlan(
        reason_code="PLAN_READY",
        actions=(
            PdfAction("GENERATE_PDF", "PLAN_READY", solicitudes=(solicitud,), persona=_persona(), destino=Path("/tmp/a.pdf")),
            PdfAction("HASH_FILE", "PLAN_READY"),
            PdfAction("UPDATE_STATUS", "PLAN_READY", solicitud=solicitud),
        ),
    )

    path, actualizadas = run_pdf_confirmadas_plan(
        plan,
        generador_pdf=pdf,
        repo=repo,
        correlation_id=None,
        logger=__import__("logging").getLogger(__name__),
        hash_file=lambda _p: order.append("HASH_FILE") or "hash",
        incident_id_factory=lambda: "INC-TEST",
        app_error_factory=lambda inc: RuntimeError(inc),
    )

    assert path == Path("/tmp/a.pdf")
    assert pdf.calls == ["GENERATE_PDF"]
    assert order == ["HASH_FILE"]
    assert [a.id for a in actualizadas] == [11]


def test_runner_plan_vacio_no_side_effects() -> None:
    repo = _Repo()
    pdf = _Pdf()
    path, actualizadas = run_pdf_confirmadas_plan(
        PdfConfirmadasPlan(actions=(), reason_code="NO_SOLICITUDES"),
        generador_pdf=pdf,
        repo=repo,
        correlation_id=None,
        logger=__import__("logging").getLogger(__name__),
        hash_file=lambda _p: "hash",
        incident_id_factory=lambda: "INC-TEST",
        app_error_factory=lambda inc: RuntimeError(inc),
    )
    assert path is None
    assert actualizadas == []
    assert pdf.calls == []
    assert repo.updated == []


def test_runner_mantiene_manejo_error_tecnico() -> None:
    class _PdfFail(_Pdf):
        def generar_pdf_solicitudes(self, *args, **kwargs):
            raise InfraError("fallo")

    plan = PdfConfirmadasPlan(
        reason_code="PLAN_READY",
        actions=(PdfAction("GENERATE_PDF", "PLAN_READY", solicitudes=(_solicitud(),), persona=_persona(), destino=Path("/tmp/a.pdf")),),
    )

    with pytest.raises(RuntimeError, match="INC-TEST"):
        run_pdf_confirmadas_plan(
            plan,
            generador_pdf=_PdfFail(),
            repo=_Repo(),
            correlation_id="corr",
            logger=__import__("logging").getLogger(__name__),
            hash_file=lambda _p: "hash",
            incident_id_factory=lambda: "INC-TEST",
            app_error_factory=lambda inc: RuntimeError(inc),
        )


def test_orquestador_invoca_builder_y_runner(monkeypatch) -> None:
    solicitud = _solicitud()
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

    import app.application.use_cases.solicitudes.use_case as uc_module

    monkeypatch.setattr(uc_module, "plan_pdf_confirmadas", _fake_builder)
    monkeypatch.setattr(uc_module, "run_pdf_confirmadas_plan", _fake_runner)

    use_case = SolicitudUseCases(_Repo(), _PersonaRepo(_persona()), config_repo=_ConfigRepo(), generador_pdf=_Pdf())
    path, actualizadas = use_case._generar_pdf_confirmadas([solicitud], Path("/tmp/x.pdf"), correlation_id=None)

    assert path is None
    assert actualizadas == [solicitud]
    assert calls == ["builder", "runner"]


def test_runner_reason_code_persona_no_encontrada() -> None:
    with pytest.raises(BusinessRuleError, match="Persona no encontrada"):
        run_pdf_confirmadas_plan(
            PdfConfirmadasPlan(actions=(), reason_code="PERSONA_NO_ENCONTRADA"),
            generador_pdf=_Pdf(),
            repo=_Repo(),
            correlation_id=None,
            logger=__import__("logging").getLogger(__name__),
            hash_file=lambda _p: "hash",
            incident_id_factory=lambda: "INC-TEST",
            app_error_factory=lambda inc: RuntimeError(inc),
        )
