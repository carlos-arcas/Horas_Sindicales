from __future__ import annotations

from app.application.dto import SolicitudDTO
from app.ui.controllers.estado_post_confirmacion import (
    EntradaEstadoPostConfirmacion,
    aplicar_confirmacion_en_lista,
    resolver_estado_post_confirmacion,
)


def _solicitud(sid: int | None) -> SolicitudDTO:
    return SolicitudDTO(
        id=sid,
        persona_id=1,
        fecha_solicitud="2025-01-01",
        fecha_pedida="2025-01-01",
        desde="09:00",
        hasta="10:00",
        completo=False,
        horas=1.0,
        observaciones=None,
        pdf_path=None,
        pdf_hash=None,
        notas=None,
    )


def test_resolver_estado_post_confirmacion_con_pendientes_restantes_explicitos() -> None:
    entrada = EntradaEstadoPostConfirmacion(
        confirmadas_ids=[1, 2],
        pendientes_restantes=[_solicitud(3)],
        pending_all_solicitudes=[_solicitud(1), _solicitud(2), _solicitud(3)],
        pending_solicitudes=[_solicitud(1), _solicitud(2), _solicitud(3)],
        hidden_pendientes=[_solicitud(2), _solicitud(3)],
        pending_otras_delegadas=[_solicitud(2), _solicitud(4)],
        orphan_pendientes=[_solicitud(3), _solicitud(5)],
    )

    estado = resolver_estado_post_confirmacion(entrada)

    assert [s.id for s in estado.pending_solicitudes] == [3]
    assert [s.id for s in estado.pending_all_solicitudes] == [3]
    assert [s.id for s in estado.hidden_pendientes] == [3]
    assert estado.pending_otras_delegadas == []
    assert estado.orphan_pendientes == [entrada.orphan_pendientes[0]]
    assert estado.confirmadas_aplicadas_ids == [1, 2]


def test_resolver_estado_post_confirmacion_sin_pendientes_restantes_deriva_desde_listas_previas() -> None:
    entrada = EntradaEstadoPostConfirmacion(
        confirmadas_ids=[2],
        pendientes_restantes=None,
        pending_all_solicitudes=[_solicitud(1), _solicitud(2), _solicitud(3)],
        pending_solicitudes=[_solicitud(2), _solicitud(3)],
        hidden_pendientes=[_solicitud(2)],
        pending_otras_delegadas=[_solicitud(2), _solicitud(9)],
        orphan_pendientes=[_solicitud(2), _solicitud(None)],
    )

    estado = resolver_estado_post_confirmacion(entrada)

    assert [s.id for s in estado.pending_all_solicitudes] == [1, 3]
    assert [s.id for s in estado.pending_solicitudes] == [3]
    assert estado.hidden_pendientes == []
    assert [s.id for s in estado.pending_otras_delegadas] == [9]
    assert [s.id for s in estado.orphan_pendientes] == [None]
    assert estado.confirmadas_aplicadas_ids == [2]


def test_aplicar_confirmacion_en_lista_cuando_no_hay_confirmadas_devuelve_intacta() -> None:
    pendientes = [_solicitud(10), _solicitud(11)]

    resultado = aplicar_confirmacion_en_lista(pendientes, [])

    assert [s.id for s in resultado] == [10, 11]
