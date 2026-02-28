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
        ({"fecha": "x", "delegada": "y"}, ("delegada", "fecha", "tramo"), "delegada"),
        ({"tramo": "x", "fecha": "y"}, ("delegada", "fecha", "tramo"), "fecha"),
        ({"x": "1", "y": "2"}, ("tramo",), "x"),
        ({"x": "1", "tramo": "2"}, ("tramo",), "tramo"),
        ({"delegada": "1", "tramo": "2"}, ("tramo", "delegada"), "tramo"),
    ],
)
def test_resolve_first_invalid_field(errors, order, expected):
    assert resolve_first_invalid_field(SolicitudesFocusInput(blocking_errors=errors, field_order=order)) == expected


@pytest.mark.parametrize(
    ("pending", "blocking", "runtime", "saved", "expected_label"),
    [
        (0, False, False, False, "Listo"),
        (0, False, False, True, "Guardado"),
        (1, False, False, False, "Pendiente de sync"),
        (2, False, False, True, "Pendiente de sync"),
        (0, True, False, False, "Error"),
        (0, False, True, False, "Error"),
        (3, True, False, False, "Error"),
        (3, False, True, False, "Error"),
        (0, True, True, True, "Error"),
        (0, False, False, False, "Listo"),
        (9, False, False, False, "Pendiente de sync"),
        (1, False, False, True, "Pendiente de sync"),
    ],
)
def test_build_solicitudes_status_label(pending, blocking, runtime, saved, expected_label):
    output = build_solicitudes_status(
        SolicitudesStatusInput(
            pending_count=pending,
            has_blocking_errors=blocking,
            has_runtime_error=runtime,
            last_action_saved=saved,
        )
    )
    assert output.label == expected_label


@pytest.mark.parametrize(
    ("pending", "blocking", "runtime", "saved", "hint_contains"),
    [
        (0, False, False, False, "nueva solicitud"),
        (0, False, False, True, "guardaron"),
        (1, False, False, False, "Google Sheets"),
        (0, True, False, False, "campos marcados"),
        (0, False, True, False, "campos marcados"),
    ],
)
def test_build_solicitudes_status_hint(pending, blocking, runtime, saved, hint_contains):
    output = build_solicitudes_status(
        SolicitudesStatusInput(
            pending_count=pending,
            has_blocking_errors=blocking,
            has_runtime_error=runtime,
            last_action_saved=saved,
        )
    )
    assert hint_contains in output.hint
