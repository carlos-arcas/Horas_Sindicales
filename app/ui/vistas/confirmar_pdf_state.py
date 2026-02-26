from __future__ import annotations


def debe_habilitar_confirmar_pdf(pendientes_count: int) -> bool:
    return pendientes_count > 0

