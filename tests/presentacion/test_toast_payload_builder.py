from __future__ import annotations

from app.ui.toasts.toast_payload_builder import ToastPayloadEntrada, construir_toast_payload


def test_payload_toast_no_generado_si_message_none() -> None:
    payload = construir_toast_payload(
        ToastPayloadEntrada(
            message=None,
            level="info",
            title=None,
            action_label=None,
            action_callback=None,
            details=None,
            correlation_id=None,
            code=None,
            origin=None,
            exc_info=None,
            duration_ms=None,
            opts={},
        )
    )

    assert payload is None


def test_payload_toast_resuelve_copys_y_detalles_tecnicos() -> None:
    payload = construir_toast_payload(
        ToastPayloadEntrada(
            message="Se produjo un error",
            level="error",
            title=None,
            action_label="Ver",
            action_callback=None,
            details=None,
            correlation_id=None,
            code=None,
            origin=None,
            exc_info=RuntimeError("fallo tecnico"),
            duration_ms=3000,
            opts={"codigo": "COD-1", "origen": "ui.prueba", "correlacion_id": "CID-9"},
        )
    )

    assert payload is not None
    assert payload.codigo == "COD-1"
    assert payload.origen == "ui.prueba"
    assert payload.correlacion_id == "CID-9"
    assert payload.dedupe_key.startswith("COD-1:ui.prueba")
    assert payload.detalles is not None and "RuntimeError" in payload.detalles


def test_payload_toast_resuelve_aliases_defaults_y_dedupe() -> None:
    payload = construir_toast_payload(
        ToastPayloadEntrada(
            message="Operacion",
            level="info",
            title=None,
            action_label=None,
            action_callback=None,
            details="detalle",
            correlation_id=None,
            code=None,
            origin=None,
            exc_info=None,
            duration_ms=None,
            opts={"codigo": "X1", "origen": "mod.ui", "correlacion_id": "CID-1"},
        )
    )

    assert payload is not None
    assert payload.codigo == "X1"
    assert payload.origen == "mod.ui"
    assert payload.correlacion_id == "CID-1"
    assert payload.duracion_ms == 8000
    assert payload.dedupe_key == "X1:mod.ui:sin_excepcion"
