from __future__ import annotations

from datetime import date, datetime, timezone

from app.application.dto import SolicitudDTO
from app.application.use_cases.exportar_compartir_periodo import EntradaExportacionPeriodo, ExportarCompartirPeriodoCasoUso
from app.application.use_cases.politica_modo_solo_lectura import crear_politica_modo_solo_lectura
from app.domain.models import Persona
from app.infrastructure.sistema_archivos.local import SistemaArchivosLocal


class RelojFijo:
    def ahora_utc(self) -> datetime:
        return datetime(2025, 1, 2, 3, 4, 5, tzinfo=timezone.utc)


class PdfFake:
    def generar_pdf_historico(self, solicitudes, persona, destino, **kwargs):
        destino.write_text("%PDF-fake", encoding="utf-8")


def _persona() -> Persona:
    return Persona(1, "Ana", "F", 0, 0, True, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)


def _solicitud() -> SolicitudDTO:
    return SolicitudDTO(1, 1, "2025-01-01", "2025-01-01", "08:00", "09:00", False, 1.0, None, None, None)


def test_integration_genera_md_y_json(tmp_path) -> None:
    caso = ExportarCompartirPeriodoCasoUso(
        fs=SistemaArchivosLocal(),
        reloj=RelojFijo(),
        exportador_pdf=PdfFake(),
        politica_modo_solo_lectura=crear_politica_modo_solo_lectura(lambda: False),
    )
    plan = caso.crear_plan(
        EntradaExportacionPeriodo(date(2025, 1, 1), date(2025, 1, 31), filtro_delegada=1, destino=tmp_path, dry_run=False),
        [_solicitud()],
        _persona(),
    )

    resultado = caso.ejecutar(plan, [_solicitud()], _persona())

    assert resultado.estado == "PASS"
    assert (tmp_path / plan.incident_id / "exportacion_auditoria.md").exists()
    assert (tmp_path / plan.incident_id / "reporte_reproducible.json").exists()
