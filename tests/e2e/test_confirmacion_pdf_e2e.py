from __future__ import annotations

import logging
from pathlib import Path

import pytest

from app.application.dto import SolicitudDTO
from app.application.use_cases.solicitudes.confirmacion_pdf_service import hash_file
from app.application.use_cases.solicitudes.pdf_confirmadas_builder import PdfConfirmadasEntrada, plan_pdf_confirmadas
from app.application.use_cases.solicitudes.pdf_confirmadas_runner import run_pdf_confirmadas_plan
from app.core import metrics as metrics_module
from app.core.errors import InfraError
from app.core.metrics import MetricsRegistry
from app.domain.models import Persona


class FakeGeneradorPdf:
    def __init__(self, destino: Path) -> None:
        self.destino = destino
        self.calls = 0

    def generar_pdf_solicitudes(self, *args, **kwargs) -> Path:
        _ = (args, kwargs)
        self.calls += 1
        self.destino.write_bytes(b"")
        return self.destino


class FakeGeneradorPdfError:
    def generar_pdf_solicitudes(self, *args, **kwargs) -> Path:
        _ = (args, kwargs)
        raise InfraError("fallo tecnico simulado")


class FakeSolicitudRepo:
    def __init__(self) -> None:
        self.updated: list[tuple[int, str, str | None]] = []

    def update_pdf_info(self, solicitud_id: int, pdf_path: str, pdf_hash: str | None) -> None:
        self.updated.append((solicitud_id, pdf_path, pdf_hash))


def _persona() -> Persona:
    return Persona(
        id=7,
        nombre="Delegada E2E",
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


def _solicitud(sid: int) -> SolicitudDTO:
    return SolicitudDTO(
        id=sid,
        persona_id=7,
        fecha_solicitud="2026-01-01",
        fecha_pedida="2026-01-02",
        desde="09:00",
        hasta="10:00",
        completo=False,
        horas=1.0,
        observaciones="ok",
        pdf_path=None,
        pdf_hash=None,
    )


@pytest.fixture
def isolated_metrics(monkeypatch: pytest.MonkeyPatch) -> MetricsRegistry:
    isolated = MetricsRegistry()
    monkeypatch.setattr(metrics_module, "metrics_registry", isolated)
    import app.application.use_cases.solicitudes.pdf_confirmadas_runner as runner_module

    monkeypatch.setattr(runner_module, "metrics_registry", isolated)
    return isolated


def _entrada(solicitudes: tuple[SolicitudDTO, ...], destino: Path) -> PdfConfirmadasEntrada:
    return PdfConfirmadasEntrada(
        creadas=solicitudes,
        destino=destino,
        persona=_persona(),
        generador_configurado=True,
        intro_text="Intro estable",
        logo_path="logo.png",
        include_hours_in_horario=True,
    )


def test_confirmacion_pdf_e2e_ok_actualiza_pdf_repo_y_metricas(tmp_path: Path, isolated_metrics: MetricsRegistry) -> None:
    solicitudes = (_solicitud(101), _solicitud(102))
    destino_pdf = tmp_path / "x.pdf"
    repo = FakeSolicitudRepo()
    generador = FakeGeneradorPdf(destino_pdf)

    plan = plan_pdf_confirmadas(_entrada(solicitudes, destino_pdf))
    before = isolated_metrics.snapshot()

    pdf_path, actualizadas = run_pdf_confirmadas_plan(
        plan,
        generador_pdf=generador,
        repo=repo,
        correlation_id="corr-e2e-ok",
        logger=logging.getLogger(__name__),
        hash_file=hash_file,
        incident_id_factory=lambda: "INC-TEST123",
        app_error_factory=lambda incident_id: RuntimeError(f"INCIDENT:{incident_id}"),
    )

    after = isolated_metrics.snapshot()

    assert pdf_path == destino_pdf
    assert generador.calls == 1
    assert [s.id for s in actualizadas] == [101, 102]
    assert all(s.pdf_path == str(destino_pdf) for s in actualizadas)
    assert all(s.pdf_hash == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855" for s in actualizadas)
    assert repo.updated == [
        (101, str(destino_pdf), "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"),
        (102, str(destino_pdf), "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"),
    ]
    assert after["counters"].get("pdfs_generados", 0) == before["counters"].get("pdfs_generados", 0) + 1
    assert after["timings_ms"]["latency.generar_pdf_ms"]["count"] == before["timings_ms"].get("latency.generar_pdf_ms", {}).get("count", 0) + 1
    assert after["timings_ms"]["latency.generar_pdf_ms"]["last"] > 0


def test_confirmacion_pdf_e2e_error_tecnico_no_persiste(tmp_path: Path, isolated_metrics: MetricsRegistry) -> None:
    solicitud = (_solicitud(201),)
    destino_pdf = tmp_path / "error.pdf"
    repo = FakeSolicitudRepo()

    plan = plan_pdf_confirmadas(_entrada(solicitud, destino_pdf))
    before = isolated_metrics.snapshot()

    with pytest.raises(RuntimeError, match="INCIDENT:INC-TEST123"):
        run_pdf_confirmadas_plan(
            plan,
            generador_pdf=FakeGeneradorPdfError(),
            repo=repo,
            correlation_id="corr-e2e-error",
            logger=logging.getLogger(__name__),
            hash_file=hash_file,
            incident_id_factory=lambda: "INC-TEST123",
            app_error_factory=lambda incident_id: RuntimeError(f"INCIDENT:{incident_id}"),
        )

    after = isolated_metrics.snapshot()
    assert repo.updated == []
    assert after["counters"].get("pdfs_generados", 0) == before["counters"].get("pdfs_generados", 0)


def test_confirmacion_pdf_e2e_plan_vacio_no_side_effects(tmp_path: Path, isolated_metrics: MetricsRegistry) -> None:
    repo = FakeSolicitudRepo()
    destino_pdf = tmp_path / "unused.pdf"

    plan = plan_pdf_confirmadas(_entrada((), destino_pdf))
    assert plan.reason_code == "NO_SOLICITUDES"

    before = isolated_metrics.snapshot()
    pdf_path, actualizadas = run_pdf_confirmadas_plan.__wrapped__(
        plan,
        generador_pdf=FakeGeneradorPdf(destino_pdf),
        repo=repo,
        correlation_id=None,
        logger=logging.getLogger(__name__),
        hash_file=hash_file,
        incident_id_factory=lambda: "INC-TEST123",
        app_error_factory=lambda incident_id: RuntimeError(f"INCIDENT:{incident_id}"),
    )
    after = isolated_metrics.snapshot()

    assert pdf_path is None
    assert actualizadas == []
    assert repo.updated == []
    assert after == before
