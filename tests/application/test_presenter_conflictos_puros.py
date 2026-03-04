from __future__ import annotations

from app.application.conflicts_service import ConflictRecord
from app.ui.conflicts_dialog.presentador_conflictos import (
    construir_fila_conflicto,
    construir_filas_conflicto,
    construir_resumen_panel_inicial,
    construir_resumen_resolucion,
    extraer_campo,
    extraer_fecha,
    formatear_tipo,
    siguiente_indice,
)


def _conflicto(**overrides):
    base = {
        "id": 1,
        "uuid": "abc-123",
        "entity_type": "solicitudes",
        "local_snapshot": {"fecha_pedida": "2025-01-01", "updated_at": "2025-01-03", "saldo": "10"},
        "remote_snapshot": {"fecha": "2025-01-02", "updated_at": "2025-01-02", "saldo": "12"},
        "detected_at": "2025-01-04",
    }
    base.update(overrides)
    return ConflictRecord(**base)


def test_transformacion_nominal_a_view_model():
    fila = construir_fila_conflicto(_conflicto(entity_type="delegadas"))

    assert fila.tipo == "delegada"
    assert fila.fecha == "2025-01-01"
    assert fila.campo == "fecha"
    assert fila.local_updated == "2025-01-03"
    assert fila.remote_updated == "2025-01-02"


def test_extraer_fecha_prioriza_local_y_maneja_vacios():
    assert extraer_fecha({"fecha": "2025-02-01"}, {"fecha": "2025-03-01"}) == "2025-02-01"
    assert extraer_fecha({"fecha": ""}, {"created_at": "2025-03-01"}) == "2025-03-01"
    assert extraer_fecha({}, {}) == ""


def test_extraer_campo_ignora_campos_tecnicos_y_fallback_por_tipo():
    conflicto_igual = _conflicto(
        entity_type="cuadrantes",
        local_snapshot={"updated_at": "2025-01-01", "dia_semana": "L"},
        remote_snapshot={"updated_at": "2025-01-02", "dia_semana": "L"},
    )
    assert extraer_campo(conflicto_igual) == "L"

    conflicto_diff = _conflicto(local_snapshot={"id": 1, "campo": "A"}, remote_snapshot={"id": 2, "campo": "B"})
    assert extraer_campo(conflicto_diff) == "campo"


def test_resumen_y_ordenacion_indices_edge_cases():
    filas = construir_filas_conflicto([_conflicto(id=7), _conflicto(id=8, uuid="xyz")])
    resumen = construir_resumen_resolucion(filas, {7, 88}, total_resueltos=3)

    assert resumen.resueltos == 3
    assert resumen.pendientes == 2
    assert resumen.revision_manual == 1
    assert siguiente_indice(None, 2) == 0
    assert siguiente_indice(0, 2) == 1
    assert siguiente_indice(1, 2) == 0
    assert siguiente_indice(None, 0) is None


def test_resumen_panel_sin_hardcodes_en_test_con_traductor_controlado():
    filas = construir_filas_conflicto([_conflicto()])
    def traductor(clave: str) -> str:
        return f"<{clave}>"

    resumen = construir_resumen_panel_inicial(filas, traductor)

    assert "<ui.conflictos.conflictos_detectados>" in resumen
    assert "<ui.conflictos.item_total> 1" in resumen


def test_formatear_tipo_valores_raros_y_none_como_desconocido():
    assert formatear_tipo("delegadas") == "delegada"
    assert formatear_tipo("otro") == "otro"
    assert formatear_tipo("") == ""
