from __future__ import annotations

from app.infrastructure.sistema_archivos.local import SistemaArchivosLocal
from pathlib import Path

import pytest

from app.application.dto import PeriodoFiltro
from app.application.use_cases import SolicitudUseCases
from app.application.use_cases.politica_modo_solo_lectura import crear_estado_modo_solo_lectura, crear_politica_modo_solo_lectura
from app.application.use_cases.confirmacion_pdf.servicio_pdf_confirmadas import hash_file
from app.core import metrics as metrics_module
from app.core.metrics import MetricsRegistry
from app.domain.models import Persona, Solicitud


class FakeGeneradorPdf:
    def __init__(self) -> None:
        self.calls = 0
        self.last_destino: Path | None = None

    def construir_nombre_archivo(self, nombre_solicitante: str, fechas: list[str]) -> str:
        _ = (nombre_solicitante, fechas)
        return "historico.pdf"

    def generar_pdf_solicitudes(self, solicitudes, persona, destino, intro_text=None, logo_path=None, include_hours_in_horario=None):
        _ = (solicitudes, persona, destino, intro_text, logo_path, include_hours_in_horario)
        raise AssertionError("No aplica para exportación de histórico")

    def generar_pdf_historico(self, solicitudes, persona, destino, intro_text=None, logo_path=None, personas_por_id=None):
        _ = (solicitudes, persona, intro_text, logo_path)
        self.calls += 1
        self.last_destino = destino
        destino.write_bytes(b"")
        return destino


class FakeSolicitudRepoHistorico:
    def __init__(self) -> None:
        self.calls: list[tuple[int, int, int | None]] = []

    def list_by_persona_and_period(self, persona_id: int, year: int, month: int | None):
        self.calls.append((persona_id, year, month))
        return [
            Solicitud(
                id=101,
                persona_id=persona_id,
                fecha_solicitud="2026-01-10",
                fecha_pedida="2026-01-15",
                desde_min=9 * 60,
                hasta_min=10 * 60,
                completo=False,
                horas_solicitadas_min=60,
                observaciones="ok",
            )
        ]


class FakePersonaRepo:
    def __init__(self, persona: Persona) -> None:
        self.persona = persona

    def get_by_id(self, persona_id: int) -> Persona | None:
        if self.persona.id == persona_id:
            return self.persona
        return None


@pytest.fixture

def isolated_metrics(monkeypatch: pytest.MonkeyPatch) -> MetricsRegistry:
    isolated = MetricsRegistry()
    monkeypatch.setattr(metrics_module, "metrics_registry", isolated)
    import app.application.use_cases.solicitudes.use_case as use_case_module

    monkeypatch.setattr(use_case_module, "metrics_registry", isolated)
    return isolated


def _persona() -> Persona:
    return Persona(
        id=7,
        nombre="Delegada Histórica",
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


def test_exportacion_pdf_historico_e2e_genera_pdf_vacio_y_metricas(tmp_path: Path, isolated_metrics: MetricsRegistry) -> None:
    persona = _persona()
    repo = FakeSolicitudRepoHistorico()
    generador = FakeGeneradorPdf()
    use_case = SolicitudUseCases(repo=repo, persona_repo=FakePersonaRepo(persona), generador_pdf=generador, fs=SistemaArchivosLocal(), politica_modo_solo_lectura=crear_politica_modo_solo_lectura(crear_estado_modo_solo_lectura(lambda: False)))

    before = isolated_metrics.snapshot()
    pdf_path = use_case.exportar_historico_pdf(
        persona_id=7,
        filtro=PeriodoFiltro.anual(2026),
        destino=tmp_path / "historico.pdf",
        correlation_id="corr-historico-e2e",
    )
    after = isolated_metrics.snapshot()

    assert pdf_path == tmp_path / "historico.pdf"
    assert pdf_path.exists()
    assert hash_file(pdf_path) == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    assert generador.calls == 1
    assert generador.last_destino == pdf_path
    assert repo.calls == [(7, 2026, None)]
    assert after["counters"].get("pdfs_generados", 0) == before["counters"].get("pdfs_generados", 0) + 1
    assert after["timings_ms"]["latency.generar_pdf_ms"]["count"] == before["timings_ms"].get(
        "latency.generar_pdf_ms", {}
    ).get("count", 0) + 1
    assert after["timings_ms"]["latency.generar_pdf_ms"]["last"] >= 0
