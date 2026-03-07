from __future__ import annotations

from app.ui.copy_catalog import copy_text
from app.ui.presentacion_confirmacion_notificaciones import construir_presentacion_confirmacion, resolver_titulo_y_borde


def test_resolver_titulo_y_borde_por_estado() -> None:
    assert resolver_titulo_y_borde("success") == (copy_text("ui.dialogo.confirmada"), "#2a9d8f")
    assert resolver_titulo_y_borde("partial") == (copy_text("ui.dialogo.con_avisos"), "#f4a261")
    assert resolver_titulo_y_borde("error") == (copy_text("ui.dialogo.error"), "#d62828")


def test_presentacion_confirmacion_es_pura_y_predecible() -> None:
    presentacion = construir_presentacion_confirmacion(
        status="partial",
        count=3,
        total_minutes=150,
        delegadas=["A", "B"],
        saldo_disponible="10:00",
        timestamp="07/03/2026 10:00:00",
        result_id="OP-0009",
        correlation_id="CID-9",
        errores=["E1", "E2", "E3", "E4"],
    )

    assert presentacion.titulo == copy_text("ui.dialogo.con_avisos")
    assert presentacion.color_borde == "#f4a261"
    assert any(copy_text("ui.notificacion.solicitudes_confirmadas") in linea and "3" in linea for linea in presentacion.lineas_resumen)
    assert any(copy_text("ui.notificacion.horas_confirmadas") in linea and "2:30" in linea for linea in presentacion.lineas_resumen)
    assert any(copy_text("ui.notificacion.id_incidente") in linea and "CID-9" in linea for linea in presentacion.lineas_resumen)
    assert presentacion.avisos == ["E1", "E2", "E3"]
