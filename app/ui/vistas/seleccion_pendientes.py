from __future__ import annotations

from typing import Iterable, Sequence


ESTADO_TOGGLE_MARCADO = "marcado"
ESTADO_TOGGLE_DESMARCADO = "desmarcado"
ESTADO_TOGGLE_PARCIAL = "parcial"


def resolver_estado_toggle(total_visibles_marcables: int, seleccionadas_visibles: int) -> str:
    if total_visibles_marcables <= 0 or seleccionadas_visibles <= 0:
        return ESTADO_TOGGLE_DESMARCADO
    if seleccionadas_visibles >= total_visibles_marcables:
        return ESTADO_TOGGLE_MARCADO
    return ESTADO_TOGGLE_PARCIAL


def construir_rango_contiguo(
    *,
    filas_visibles_marcables: Sequence[int],
    fila_ancla: int,
    fila_destino: int,
) -> list[int]:
    posiciones = {fila: indice for indice, fila in enumerate(filas_visibles_marcables)}
    if fila_ancla not in posiciones or fila_destino not in posiciones:
        return [fila_destino] if fila_destino in posiciones else []

    inicio = posiciones[fila_ancla]
    fin = posiciones[fila_destino]
    if inicio > fin:
        inicio, fin = fin, inicio
    return list(filas_visibles_marcables[inicio : fin + 1])


def filtrar_filas_marcables(
    *,
    filas: Iterable[int],
    filas_ocultas: set[int],
    filas_no_marcables: set[int],
) -> list[int]:
    return [
        fila
        for fila in filas
        if fila not in filas_ocultas and fila not in filas_no_marcables
    ]
