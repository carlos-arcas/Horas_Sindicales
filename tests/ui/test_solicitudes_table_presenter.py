from __future__ import annotations

import pytest

from app.ui.models.solicitudes_table_presenter import SolicitudDisplayEntrada, build_display

pytestmark = pytest.mark.headless_safe


@pytest.mark.parametrize(
    ("column", "kwargs", "expected"),
    [
        (0, {}, "2026-01-10"),
        (1, {"desde": ""}, "-"),
        (1, {"desde": None}, "-"),
        (1, {"desde": "08:30"}, "08:30"),
        (2, {"hasta": ""}, "-"),
        (2, {"hasta": None}, "-"),
        (2, {"hasta": "11:00"}, "11:00"),
        (3, {"completo": True}, "Sí"),
        (3, {"completo": False}, "No"),
        (4, {"horas": 0}, "00:00"),
        (4, {"horas": 1.5}, "01:30"),
        (4, {"horas": -2.0}, "-02:00"),
        (4, {"horas": 1 / 60}, "00:01"),
        (5, {"notas": None}, ""),
        (5, {"notas": ""}, ""),
        (5, {"notas": "Observación"}, "Observación"),
    ],
)
def test_build_display_columnas_base(column: int, kwargs: dict, expected: str) -> None:
    entrada = SolicitudDisplayEntrada(
        column=column,
        fecha_pedida="2026-01-10",
        desde="09:00",
        hasta="10:00",
        completo=False,
        horas=2.0,
        notas="Nota",
        generated=False,
        show_estado=False,
        show_delegada=False,
        **kwargs,
    )

    assert build_display(entrada).texto_display == expected


@pytest.mark.parametrize(
    ("generated", "is_deleted", "expected"),
    [
        (True, False, "✅ Confirmada"),
        (False, False, "🕒 Pendiente"),
        (True, True, "🗑 Eliminada"),
        (False, True, "🗑 Eliminada"),
    ],
)
def test_build_display_estado_precedencia(generated: bool, is_deleted: bool, expected: str) -> None:
    entrada = SolicitudDisplayEntrada(
        column=6,
        fecha_pedida="2026-01-10",
        desde="09:00",
        hasta="10:00",
        completo=False,
        horas=2.0,
        notas="Nota",
        generated=generated,
        show_estado=True,
        show_delegada=False,
        is_deleted=is_deleted,
    )

    assert build_display(entrada).texto_display == expected


@pytest.mark.parametrize(
    ("show_estado", "show_delegada", "column", "persona_nombre", "expected"),
    [
        (False, True, 6, None, "(sin delegada)"),
        (False, True, 6, "Ana", "Ana"),
        (True, True, 7, None, "(sin delegada)"),
        (True, True, 7, "Bea", "Bea"),
        (True, False, 7, "Carla", None),
    ],
)
def test_build_display_columna_delegada(
    show_estado: bool,
    show_delegada: bool,
    column: int,
    persona_nombre: str | None,
    expected: str | None,
) -> None:
    entrada = SolicitudDisplayEntrada(
        column=column,
        fecha_pedida="2026-01-10",
        desde="09:00",
        hasta="10:00",
        completo=False,
        horas=2.0,
        notas="Nota",
        generated=False,
        show_estado=show_estado,
        show_delegada=show_delegada,
        persona_nombre=persona_nombre,
    )

    assert build_display(entrada).texto_display == expected


def test_build_display_contratos_texto_criticos() -> None:
    assert (
        build_display(
            SolicitudDisplayEntrada(
                column=3,
                fecha_pedida="2026-01-10",
                desde="09:00",
                hasta="10:00",
                completo=True,
                horas=2.0,
                notas="Nota",
                generated=False,
                show_estado=False,
                show_delegada=False,
            )
        ).texto_display
        == "Sí"
    )
    assert (
        build_display(
            SolicitudDisplayEntrada(
                column=4,
                fecha_pedida="2026-01-10",
                desde="09:00",
                hasta="10:00",
                completo=False,
                horas=1.5,
                notas="Nota",
                generated=False,
                show_estado=False,
                show_delegada=False,
            )
        ).texto_display
        == "01:30"
    )
    assert (
        build_display(
            SolicitudDisplayEntrada(
                column=6,
                fecha_pedida="2026-01-10",
                desde="09:00",
                hasta="10:00",
                completo=False,
                horas=2.0,
                notas="Nota",
                generated=False,
                show_estado=True,
                show_delegada=False,
            )
        ).texto_display
        == "🕒 Pendiente"
    )
    assert (
        build_display(
            SolicitudDisplayEntrada(
                column=6,
                fecha_pedida="2026-01-10",
                desde="09:00",
                hasta="10:00",
                completo=False,
                horas=2.0,
                notas="Nota",
                generated=True,
                show_estado=True,
                show_delegada=False,
            )
        ).texto_display
        == "✅ Confirmada"
    )
