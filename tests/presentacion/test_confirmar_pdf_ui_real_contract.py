from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

from app.application.dto import SolicitudDTO
from app.bootstrap.container import build_container
from app.infrastructure.db import configure_sqlite_connection
from app.testing.qt_harness import (
    importar_qt_para_ui_real_o_skip,
    preparar_entorno_qt_headless,
)

if TYPE_CHECKING:
    from app.ui.main_window import MainWindow


class _SinRedSheetsService:
    def is_configured(self) -> bool:
        return False

    def __getattr__(self, _name: str):
        return lambda *args, **kwargs: None


def _connection_factory(db_path: Path):
    def _build() -> sqlite3.Connection:
        connection = sqlite3.connect(db_path)
        configure_sqlite_connection(connection)
        return connection

    return _build


def _agregar_pendiente(container, persona_id: int, fecha: str) -> int:
    creada, _ = container.solicitud_use_cases.agregar_solicitud(
        SolicitudDTO(
            id=None,
            persona_id=persona_id,
            fecha_solicitud="2026-02-01",
            fecha_pedida=fecha,
            desde="09:00",
            hasta="10:00",
            completo=False,
            horas=1.0,
            observaciones="contrato ui real",
            pdf_path=None,
            pdf_hash=None,
            notas="prioridad 1",
        ),
        correlation_id=f"corr-ui-real-{fecha}",
    )
    assert creada.id is not None
    return int(creada.id)


def _seleccionar_filas(
    window: MainWindow, rows: list[int], qitem_selection_model: Any
) -> list[int]:
    selection_model = window.pendientes_table.selectionModel()
    assert selection_model is not None
    selection_model.clearSelection()
    model = window.pendientes_table.model()
    assert model is not None

    for row in rows:
        index = model.index(row, 0)
        selection_model.select(
            index,
            qitem_selection_model.SelectionFlag.Select
            | qitem_selection_model.SelectionFlag.Rows,
        )
    return window._obtener_ids_seleccionados_pendientes()


@pytest.mark.ui
def test_confirmar_pdf_ui_real_contract(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    entorno_qt = preparar_entorno_qt_headless()
    qt_widgets, qt_core = importar_qt_para_ui_real_o_skip()
    qapplication = qt_widgets.QApplication
    qfile_dialog = qt_widgets.QFileDialog
    qitem_selection_model = qt_core.QItemSelectionModel

    from app.ui.main_window import MainWindow
    from app.ui.vistas import confirmacion_actions

    app = qapplication.instance() or qapplication([])
    db_path = tmp_path / "runtime_ui_real.sqlite3"
    pdf_dir = tmp_path / "salida_pdf"
    pdf_dir.mkdir(parents=True, exist_ok=True)

    container = build_container(connection_factory=_connection_factory(db_path))
    container.sheets_service = _SinRedSheetsService()

    window = MainWindow(
        container.persona_use_cases,
        container.solicitud_use_cases,
        container.grupo_use_cases,
        container.sheets_service,
        container.sync_service,
        container.conflicts_service,
        health_check_use_case=container.health_check_use_case,
        alert_engine=container.alert_engine,
        validacion_preventiva_lock_use_case=container.validacion_preventiva_lock_use_case,
        confirmar_pendientes_pdf_caso_uso=container.confirmar_pendientes_pdf_caso_uso,
        crear_pendiente_caso_uso=container.crear_pendiente_caso_uso,
        servicio_i18n=container.servicio_i18n,
        estado_modo_solo_lectura=container.estado_modo_solo_lectura,
    )

    save_calls: list[str] = []
    open_calls: list[str] = []
    evidencia_path = tmp_path / "evidencia_confirmar_pdf_ui_real.json"

    def _fake_save(*_args, **_kwargs):
        path = pdf_dir / f"confirmacion_{len(save_calls) + 1}.pdf"
        save_calls.append(str(path))
        return str(path), "pdf"

    def _fake_open(path: Path) -> None:
        open_calls.append(str(path))

    monkeypatch.setattr(qfile_dialog, "getSaveFileName", _fake_save)
    monkeypatch.setattr(confirmacion_actions, "abrir_archivo_local", _fake_open)
    monkeypatch.setattr(window, "_ask_push_after_pdf", lambda: None)
    monkeypatch.setattr(window, "_show_pdf_actions_dialog", lambda _path: None)

    try:
        window._reload_pending_views()
        app.processEvents()
        persona = window._current_persona()
        assert persona is not None and persona.id is not None

        _agregar_pendiente(container, int(persona.id), "2026-02-10")
        _agregar_pendiente(container, int(persona.id), "2026-02-11")
        window._reload_pending_views()
        app.processEvents()

        historico_inicial = len(list(container.solicitud_use_cases.listar_historico()))
        pendientes_inicial = len(window._pending_solicitudes)
        assert pendientes_inicial >= 2

        window.pendientes_table.clearSelection()
        window._on_confirmar()
        app.processEvents()

        assert len(save_calls) == 0
        assert len(open_calls) == 0
        assert len(window._pending_solicitudes) == pendientes_inicial
        assert (
            len(list(container.solicitud_use_cases.listar_historico()))
            == historico_inicial
        )

        selected_ids_s2 = _seleccionar_filas(window, [0, 1], qitem_selection_model)
        window.abrir_pdf_check.setChecked(False)
        window._on_confirmar()
        app.processEvents()

        pdf_path_s2 = Path(save_calls[-1])
        assert pdf_path_s2.exists()
        assert pdf_path_s2.stat().st_size > 0
        assert pdf_path_s2.read_bytes()[:4] == b"%PDF"
        assert len(window._pending_solicitudes) == 0
        historico_s2 = len(list(container.solicitud_use_cases.listar_historico()))
        assert historico_s2 >= historico_inicial + len(selected_ids_s2)
        assert len(open_calls) == 0

        _agregar_pendiente(container, int(persona.id), "2026-02-12")
        window._reload_pending_views()
        app.processEvents()

        selected_ids_s3 = _seleccionar_filas(window, [0], qitem_selection_model)
        window.abrir_pdf_check.setChecked(True)
        window._on_confirmar()
        app.processEvents()

        pdf_path_s3 = Path(save_calls[-1])
        assert pdf_path_s3.exists()
        assert pdf_path_s3.read_bytes()[:4] == b"%PDF"
        assert len(
            list(container.solicitud_use_cases.listar_historico())
        ) >= historico_s2 + len(selected_ids_s3)
        assert open_calls == [str(pdf_path_s3)]

        evidencia = {
            "entorno_qt": entorno_qt,
            "escenarios_ejecutados": [
                "sin_seleccion",
                "confirmacion_pdf_toggle_off",
                "confirmacion_pdf_toggle_on",
            ],
            "ids_seleccionados_escenario_2": selected_ids_s2,
            "ids_seleccionados_escenario_3": selected_ids_s3,
            "ruta_pdf_escenario_2": str(pdf_path_s2),
            "ruta_pdf_escenario_3": str(pdf_path_s3),
            "existe_pdf_escenario_2": pdf_path_s2.exists(),
            "existe_pdf_escenario_3": pdf_path_s3.exists(),
            "tamano_pdf_escenario_2": pdf_path_s2.stat().st_size,
            "tamano_pdf_escenario_3": pdf_path_s3.stat().st_size,
            "filas_pendientes_restantes": len(window._pending_solicitudes),
            "filas_historico": len(
                list(container.solicitud_use_cases.listar_historico())
            ),
            "save_calls": save_calls,
            "open_calls": open_calls,
            "qt_qpa_platform": os.environ.get("QT_QPA_PLATFORM"),
            "qt_opengl": os.environ.get("QT_OPENGL"),
        }
        evidencia_path.write_text(
            json.dumps(evidencia, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        assert evidencia_path.exists()
    finally:
        window.close()
        app.processEvents()
