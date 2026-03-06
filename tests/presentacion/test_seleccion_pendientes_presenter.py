from __future__ import annotations

from app.ui.vistas.seleccion_pendientes import (
    ESTADO_TOGGLE_DESMARCADO,
    ESTADO_TOGGLE_MARCADO,
    ESTADO_TOGGLE_PARCIAL,
    construir_rango_contiguo,
    resolver_estado_toggle,
)


def test_resolver_estado_toggle_refleja_desmarcado_parcial_y_marcado() -> None:
    assert resolver_estado_toggle(total_visibles_marcables=0, seleccionadas_visibles=0) == ESTADO_TOGGLE_DESMARCADO
    assert resolver_estado_toggle(total_visibles_marcables=3, seleccionadas_visibles=0) == ESTADO_TOGGLE_DESMARCADO
    assert resolver_estado_toggle(total_visibles_marcables=3, seleccionadas_visibles=1) == ESTADO_TOGGLE_PARCIAL
    assert resolver_estado_toggle(total_visibles_marcables=3, seleccionadas_visibles=3) == ESTADO_TOGGLE_MARCADO


def test_construir_rango_contiguo_respeta_orden_visual() -> None:
    filas_visibles = [4, 2, 7, 1]

    assert construir_rango_contiguo(
        filas_visibles_marcables=filas_visibles,
        fila_ancla=2,
        fila_destino=1,
    ) == [2, 7, 1]

    assert construir_rango_contiguo(
        filas_visibles_marcables=filas_visibles,
        fila_ancla=4,
        fila_destino=7,
    ) == [4, 2, 7]


def test_construir_rango_contiguo_fuera_de_contexto_devuelve_destino_si_es_visible() -> None:
    filas_visibles = [10, 11, 12]

    assert construir_rango_contiguo(
        filas_visibles_marcables=filas_visibles,
        fila_ancla=99,
        fila_destino=11,
    ) == [11]

    assert construir_rango_contiguo(
        filas_visibles_marcables=filas_visibles,
        fila_ancla=99,
        fila_destino=88,
    ) == []
