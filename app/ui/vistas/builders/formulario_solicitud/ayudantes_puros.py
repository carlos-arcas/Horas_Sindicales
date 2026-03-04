from __future__ import annotations


def calcular_altura_compacta_texto(
    lineas_visibles: int,
    altura_linea: int,
    margen_documento: int,
    altura_borde: int,
) -> int:
    return (altura_linea * lineas_visibles) + margen_documento + altura_borde
