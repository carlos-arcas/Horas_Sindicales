from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path

from app.application.dto import SolicitudDTO
from app.application.use_cases.politica_modo_solo_lectura import (
    MENSAJE_MODO_SOLO_LECTURA,
    crear_politica_modo_solo_lectura,
)
from app.application.use_cases.exportar_compartir_periodo import (
    EntradaExportacionPeriodo,
    ExportarCompartirPeriodoCasoUso,
)
from app.domain.models import Persona
from app.domain.services import BusinessRuleError


class FsFake:
    def __init__(self) -> None:
        self.writes: dict[str, str] = {}
        self.mkdirs: list[str] = []

    def existe(self, ruta: Path) -> bool:
        return str(ruta) in self.writes or str(ruta) in self.mkdirs

    def leer_texto(self, ruta: Path) -> str:
        return self.writes[str(ruta)]

    def leer_bytes(self, ruta: Path) -> bytes:
        return b""

    def escribir_texto(self, ruta: Path, contenido: str) -> None:
        self.writes[str(ruta)] = contenido

    def escribir_bytes(self, ruta: Path, contenido: bytes) -> None:
        self.writes[str(ruta)] = contenido.decode("utf-8")

    def mkdir(self, ruta: Path, *, parents: bool = True, exist_ok: bool = True) -> None:
        self.mkdirs.append(str(ruta))

    def listar(self, base: Path) -> list[Path]:
        return []


class RelojFijo:
    def ahora_utc(self) -> datetime:
        return datetime(2025, 1, 2, 3, 4, 5, tzinfo=timezone.utc)


class PdfFake:
    def generar_pdf_historico(self, solicitudes, persona, destino: Path, **kwargs):
        return None


def _persona() -> Persona:
    return Persona(1, "Ana", "F", 0, 0, True, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)


def _solicitud() -> SolicitudDTO:
    return SolicitudDTO(1, 1, "2025-01-01", "2025-01-01", "08:00", "09:00", False, 1.0, None, None, None)


def test_crear_plan_es_puro_sin_io() -> None:
    fs = FsFake()
    caso = ExportarCompartirPeriodoCasoUso(
        fs=fs,
        reloj=RelojFijo(),
        exportador_pdf=PdfFake(),
        politica_modo_solo_lectura=crear_politica_modo_solo_lectura(lambda: False),
    )

    plan = caso.crear_plan(
        EntradaExportacionPeriodo(fecha_desde=date(2025, 1, 1), fecha_hasta=date(2025, 1, 31), filtro_delegada=1),
        [_solicitud()],
        _persona(),
    )

    assert plan.incident_id == "EXP-20250102-030405"
    assert plan.conteo_previsto == 1
    assert fs.writes == {}


def test_ejecutar_con_fakes_genera_auditoria(tmp_path: Path) -> None:
    fs = FsFake()
    caso = ExportarCompartirPeriodoCasoUso(
        fs=fs,
        reloj=RelojFijo(),
        exportador_pdf=PdfFake(),
        politica_modo_solo_lectura=crear_politica_modo_solo_lectura(lambda: False),
    )
    plan = caso.crear_plan(
        EntradaExportacionPeriodo(
            fecha_desde=date(2025, 1, 1),
            fecha_hasta=date(2025, 1, 31),
            filtro_delegada=1,
            destino=tmp_path,
            dry_run=False,
        ),
        [_solicitud()],
        _persona(),
    )

    resultado = caso.ejecutar(plan, [_solicitud()], _persona())

    assert resultado.estado == "PASS"
    assert any(ruta.endswith("exportacion_auditoria.md") for ruta in resultado.artefactos_generados)
    assert any("reporte_reproducible.json" in ruta for ruta in fs.writes)


def test_exportacion_bloqueada_en_read_only_sin_side_effects(tmp_path: Path) -> None:
    fs = FsFake()
    caso = ExportarCompartirPeriodoCasoUso(
        fs=fs,
        reloj=RelojFijo(),
        exportador_pdf=PdfFake(),
        politica_modo_solo_lectura=crear_politica_modo_solo_lectura(lambda: True),
    )
    plan = caso.crear_plan(
        EntradaExportacionPeriodo(
            fecha_desde=date(2025, 1, 1),
            fecha_hasta=date(2025, 1, 31),
            filtro_delegada=1,
            destino=tmp_path,
            dry_run=False,
        ),
        [_solicitud()],
        _persona(),
    )

    try:
        caso.ejecutar(plan, [_solicitud()], _persona())
    except BusinessRuleError as exc:
        assert str(exc) == MENSAJE_MODO_SOLO_LECTURA
    else:
        raise AssertionError("Debe bloquear la exportación persistente en modo solo lectura")

    assert fs.mkdirs == []
    assert fs.writes == {}
