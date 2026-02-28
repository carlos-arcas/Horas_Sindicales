from __future__ import annotations

import pytest

from app.application.dto import SolicitudDTO
from app.application.use_cases.solicitudes.validaciones import detectar_duplicados_en_pendientes
from app.ui.vistas.solicitudes_presenter import (
    ActionStateInput,
    DuplicateSearchInput,
    PreventiveValidationViewInput,
    build_action_state,
    build_preventive_validation_view_model,
    find_pending_duplicate_row,
)


def _solicitud(*, id: int | None, persona_id: int = 1, fecha: str = "2026-01-10", desde: str | None = "08:00", hasta: str | None = "10:00", completo: bool = False) -> SolicitudDTO:
    return SolicitudDTO(
        id=id,
        persona_id=persona_id,
        fecha_solicitud="2026-01-01",
        fecha_pedida=fecha,
        desde=desde,
        hasta=hasta,
        completo=completo,
        horas=2,
        observaciones=None,
        pdf_path=None,
        pdf_hash=None,
        notas=None,
        generated=False,
    )


@pytest.mark.parametrize(
    ("blocking", "touched", "has_dup", "expected"),
    [
        ({}, set(), False, ("", "", "", "", False, False)),
        ({"delegada": "⚠ Selecciona"}, {"delegada"}, False, ("⚠ Selecciona", "", "", "• ⚠ Selecciona", True, False)),
        ({"fecha": "⚠ Fecha"}, set(), False, ("", "", "", "• ⚠ Fecha", True, False)),
        ({"tramo": "⚠ Tramo", "saldo": "Saldo insuficiente"}, {"tramo"}, False, ("", "", "⚠ Tramo", "• ⚠ Tramo\n• Saldo insuficiente", True, False)),
        ({"duplicado": "⚠ Existe"}, {"delegada"}, True, ("", "", "", "• ⚠ Existe", True, True)),
        ({"delegada": "d", "fecha": "f", "tramo": "t"}, {"delegada", "fecha", "tramo"}, False, ("d", "f", "t", "• d\n• f\n• t", True, False)),
    ],
)
def test_build_preventive_validation_view_model(blocking, touched, has_dup, expected):
    vm = build_preventive_validation_view_model(
        PreventiveValidationViewInput(
            blocking_errors=blocking,
            field_touched=touched,
            has_duplicate_target=has_dup,
        )
    )
    assert (vm.delegada_error, vm.fecha_error, vm.tramo_error, vm.summary_text, vm.show_pending_errors_frame, vm.show_duplicate_cta) == expected


@pytest.mark.parametrize(
    ("entrada", "expected"),
    [
        (ActionStateInput(False, False, False, False, False, False, 0, 0), (False, "Añadir pendiente", False, False, False, False, "Eliminar (0)", "Exportar histórico PDF (0)", False)),
        (ActionStateInput(True, False, False, False, False, False, 0, 0), (False, "Añadir pendiente", False, False, True, True, "Eliminar (0)", "Exportar histórico PDF (0)", False)),
        (ActionStateInput(True, True, False, False, False, False, 0, 0), (True, "Añadir pendiente", False, False, True, True, "Eliminar (0)", "Exportar histórico PDF (0)", False)),
        (ActionStateInput(True, True, True, False, True, False, 2, 0), (False, "Añadir pendiente", False, True, True, True, "Eliminar (0)", "Exportar histórico PDF (0)", True)),
        (ActionStateInput(True, True, False, True, True, False, 3, 2), (True, "Actualizar pendiente", True, True, True, True, "Eliminar (2)", "Exportar histórico PDF (2)", True)),
        (ActionStateInput(True, True, False, False, True, True, 3, 1), (True, "Añadir pendiente", False, True, True, True, "Eliminar (1)", "Exportar histórico PDF (1)", True)),
    ],
)
def test_build_action_state(entrada, expected):
    output = build_action_state(entrada)
    assert (
        output.agregar_enabled,
        output.agregar_text,
        output.insertar_sin_pdf_enabled,
        output.pendientes_count > 0,
        output.edit_persona_enabled,
        output.delete_persona_enabled,
        output.eliminar_text,
        output.generar_pdf_text,
        output.eliminar_pendiente_enabled,
    ) == expected


@pytest.mark.parametrize(
    ("pending", "solicitud", "editing_id", "editing_row", "expected"),
    [
        ([], _solicitud(id=None), None, None, None),
        ([_solicitud(id=1)], _solicitud(id=None), None, None, None),
        ([_solicitud(id=1), _solicitud(id=2)], _solicitud(id=None), None, None, 0),
        ([_solicitud(id=1), _solicitud(id=2)], _solicitud(id=None), 1, 0, 1),
        ([_solicitud(id=None), _solicitud(id=2)], _solicitud(id=None), None, 0, 1),
        ([_solicitud(id=5, desde="09:00", hasta="11:00")], _solicitud(id=None, desde="08:00", hasta="10:00"), None, None, None),
    ],
)
def test_find_pending_duplicate_row(pending, solicitud, editing_id, editing_row, expected):
    duplicated_keys = detectar_duplicados_en_pendientes(pending)
    row = find_pending_duplicate_row(
        DuplicateSearchInput(
            solicitud=solicitud,
            pending_solicitudes=pending,
            editing_pending_id=editing_id,
            editing_row=editing_row,
            duplicated_keys=duplicated_keys,
        )
    )
    assert row == expected
