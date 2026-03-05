from __future__ import annotations

import pytest

from app.ui.vistas.solicitudes_ux_rules import (
    SolicitudesFocusInput,
    SolicitudesStatusInput,
    build_solicitudes_status,
    resolve_first_invalid_field,
)


@pytest.mark.parametrize(
    ("errors", "order", "expected"),
    [
        ({}, ("delegada", "fecha", "tramo"), None),
        ({"delegada": "x"}, ("delegada", "fecha", "tramo"), "delegada"),
        ({"fecha": "x"}, ("delegada", "fecha", "tramo"), "fecha"),
        ({"tramo": "x"}, ("delegada", "fecha", "tramo"), "tramo"),
        ({"otro": "x"}, ("delegada", "fecha", "tramo"), "otro"),
    ],
)
def test_resolve_first_invalid_field(errors, order, expected):
    assert resolve_first_invalid_field(SolicitudesFocusInput(blocking_errors=errors, field_order=order)) == expected


def test_resumen_operativo_sin_delegada_y_sin_seleccion() -> None:
    salida = build_solicitudes_status(
        SolicitudesStatusInput(
            delegada_actual=None,
            pendientes_visibles=0,
            pendientes_seleccionadas=0,
            saldo_reservado="00:00",
            has_blocking_errors=False,
            has_runtime_error=False,
            hay_conflictos_pendientes=False,
            puede_confirmar_pdf=False,
        )
    )
    assert salida.label_key == "solicitudes.resumen_operativo.estado_sin_delegada"
    assert salida.action_key == "solicitudes.resumen_operativo.accion_seleccionar_delegada"
    assert salida.help_key == "solicitudes.resumen_operativo.ayuda_seleccionar_delegada"
    assert salida.label_params["seleccion_key"] == "solicitudes.resumen_operativo.seleccion_ninguna"


def test_resumen_operativo_con_conflicto_pendientes() -> None:
    salida = build_solicitudes_status(
        SolicitudesStatusInput(
            delegada_actual="Ana",
            pendientes_visibles=2,
            pendientes_seleccionadas=1,
            saldo_reservado="03:30",
            has_blocking_errors=False,
            has_runtime_error=False,
            hay_conflictos_pendientes=True,
            puede_confirmar_pdf=False,
        )
    )
    assert salida.label_key == "solicitudes.resumen_operativo.estado_con_conflictos"
    assert salida.action_key == "solicitudes.resumen_operativo.accion_corregir_conflictos"
    assert salida.help_key == "solicitudes.resumen_operativo.ayuda_conflictos"


def test_resumen_operativo_lista_para_confirmar_generar_pdf() -> None:
    salida = build_solicitudes_status(
        SolicitudesStatusInput(
            delegada_actual="Ana",
            pendientes_visibles=2,
            pendientes_seleccionadas=2,
            saldo_reservado="04:00",
            has_blocking_errors=False,
            has_runtime_error=False,
            hay_conflictos_pendientes=False,
            puede_confirmar_pdf=True,
        )
    )
    assert salida.label_key == "solicitudes.resumen_operativo.estado_lista_para_confirmar"
    assert salida.action_key == "solicitudes.resumen_operativo.accion_confirmar_generar_pdf"
    assert salida.help_key is None


def test_resumen_operativo_ayuda_contextual_vacia_si_no_aplica() -> None:
    salida = build_solicitudes_status(
        SolicitudesStatusInput(
            delegada_actual="Ana",
            pendientes_visibles=1,
            pendientes_seleccionadas=1,
            saldo_reservado="01:30",
            has_blocking_errors=False,
            has_runtime_error=False,
            hay_conflictos_pendientes=False,
            puede_confirmar_pdf=True,
        )
    )
    assert salida.help_key is None
