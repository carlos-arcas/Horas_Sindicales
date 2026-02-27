from __future__ import annotations

import runpy

from app.application.dto import SolicitudDTO
from app.application.use_cases import sync_sheets as fachada_sync
from app.application.use_cases.sync_sheets.conflicts import is_conflict, parse_iso
from app.application.use_cases.sync_sheets.reporting import (
    build_sync_report,
    render_report_json,
    render_report_md,
)
from app.application.use_cases.sync_sheets.types import Conflict, SyncItem, SyncPlan, SyncReport
from app.domain.sync_models import SyncExecutionPlan, SyncPlanItem, SyncSummary
from app.pdf.service import generate


def test_fachada_sync_exporta_api_publica() -> None:
    assert fachada_sync.SheetsSyncService is not None
    assert isinstance(fachada_sync.HEADER_CANONICO_SOLICITUDES, list)
    assert "uuid" in fachada_sync.HEADER_CANONICO_SOLICITUDES


def test_parse_iso_acepta_zulu() -> None:
    salida = parse_iso("2026-01-01T10:00:00Z")
    assert salida is not None
    assert salida.utcoffset() is not None


def test_parse_iso_devuelve_none_con_invalido() -> None:
    assert parse_iso("fecha-rota") is None


def test_parse_iso_devuelve_none_con_vacio() -> None:
    assert parse_iso("") is None


def test_is_conflict_detecta_cambios_en_ambos_lados() -> None:
    assert is_conflict("2026-01-03T10:00:00", "2026-01-03T11:00:00", "2026-01-02T00:00:00") is True


def test_is_conflict_devuelve_false_sin_last_sync() -> None:
    assert is_conflict("2026-01-03T10:00:00", "2026-01-03T11:00:00", None) is False


def test_is_conflict_devuelve_false_con_fechas_invalidas() -> None:
    assert is_conflict("rota", "2026-01-03T11:00:00", "2026-01-02T00:00:00") is False


def test_reporting_construye_diccionario() -> None:
    resumen = SyncSummary(inserted_local=1, updated_remote=2, errors=3, omitted_by_delegada=4)
    reporte = build_sync_report(resumen)
    assert reporte["inserted_local"] == 1
    assert reporte["updated_remote"] == 2
    assert reporte["errors"] == 3
    assert reporte["omitted_by_delegada"] == 4


def test_reporting_json_ordenado() -> None:
    resumen = SyncSummary(inserted_local=1)
    render = render_report_json(resumen)
    assert render.startswith("{")
    assert '"inserted_local": 1' in render


def test_reporting_md_contiene_metricas() -> None:
    resumen = SyncSummary(conflicts_detected=2)
    render = render_report_md(resumen)
    assert "# SyncReport" in render
    assert "**conflicts_detected**: 2" in render


def test_types_dataclasses_guardan_shape() -> None:
    item_plan = SyncPlanItem(uuid="u-1", action="create")
    plan = SyncExecutionPlan(generated_at="2026-01-01T00:00:00", worksheet="solicitudes", to_create=(item_plan,))
    resumen = SyncSummary(inserted_local=7)

    conflicto = Conflict("solicitudes", "u-1", {"x": 1}, {"x": 2})
    item = SyncItem(item=item_plan)
    contenedor_plan = SyncPlan(plan=plan)
    reporte = SyncReport(summary=resumen)

    assert conflicto.record_uuid == "u-1"
    assert item.item.action == "create"
    assert contenedor_plan.plan.has_changes is True
    assert reporte.summary.inserted_local == 7
    assert reporte.metadata == {}


def test_generate_pdf_hook_no_falla_con_lista_vacia() -> None:
    assert generate([]) is None


def test_generate_pdf_hook_no_falla_con_solicitudes() -> None:
    solicitud = SolicitudDTO(
        id=1,
        persona_id=1,
        fecha_solicitud="2026-01-01",
        fecha_pedida="2026-01-01",
        desde="09:00",
        hasta="10:00",
        completo=False,
        horas=1.0,
        observaciones="",
        pdf_path=None,
        pdf_hash=None,
    )
    assert generate([solicitud]) is None


def test_migrations_cli_ejecuta_main_monkeypatch(monkeypatch) -> None:
    monkeypatch.setattr("app.infrastructure.migrations.main", lambda: 9)
    try:
        runpy.run_module("app.infrastructure.migrations_cli", run_name="__main__")
    except SystemExit as exc:
        assert exc.code == 9
    else:
        raise AssertionError("Se esperaba salida por SystemExit")
