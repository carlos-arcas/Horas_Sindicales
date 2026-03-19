from __future__ import annotations

from types import SimpleNamespace

from app.ui.vistas.confirmacion_presentador_pendientes import (
    calcular_filtro_delegada_para_confirmacion,
    contar_pendientes_restantes,
    filtrar_pendientes_restantes,
    obtener_pendientes_visibles_confirmables,
    seleccionar_creadas_por_ids,
)


def test_calcular_filtro_delegada_para_confirmacion_respeta_vista_todas() -> None:
    assert calcular_filtro_delegada_para_confirmacion(True, 9) is None
    assert calcular_filtro_delegada_para_confirmacion(False, 9) == 9


def test_seleccionar_creadas_por_ids_filtra_por_ids_confirmadas() -> None:
    seleccion = [
        SimpleNamespace(id=1, persona_id=10),
        SimpleNamespace(id=2, persona_id=10),
        SimpleNamespace(id=3, persona_id=11),
    ]

    creadas = seleccionar_creadas_por_ids(seleccion, [2, 3])

    assert [sol.id for sol in creadas] == [2, 3]


def test_filtrar_y_contar_pendientes_restantes() -> None:
    pendientes = [
        SimpleNamespace(id=1, persona_id=10),
        SimpleNamespace(id=2, persona_id=10),
        SimpleNamespace(id=None, persona_id=11),
    ]

    filtradas = filtrar_pendientes_restantes(pendientes, [2])

    assert filtradas is not None
    assert [sol.id for sol in filtradas] == [2, None]
    assert contar_pendientes_restantes(filtradas) == 2
    assert contar_pendientes_restantes(None) == 0


def test_obtener_pendientes_visibles_confirmables_ignora_ausentes_y_conserva_visibles() -> None:
    visibles = [
        SimpleNamespace(id=1, persona_id=10),
        None,
        SimpleNamespace(id=2, persona_id=11),
    ]

    resultado = obtener_pendientes_visibles_confirmables(visibles)

    assert [sol.id for sol in resultado] == [1, 2]
