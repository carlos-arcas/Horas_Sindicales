from __future__ import annotations

import pytest

from app.ui.vistas.pendientes_iter_presenter import (
    IterPendientesEntrada,
    PendienteRowSnapshot,
    plan_iter_pendientes,
)


def _row(
    row: int,
    *,
    solicitud_id: int | None = 10,
    persona_id: int | None = 20,
    fecha_raw: object = "2026-01-01",
    desde_raw: object = "08:00",
    hasta_raw: object = "10:00",
    delegada_raw: object = "Ana",
) -> PendienteRowSnapshot:
    return PendienteRowSnapshot(
        row=row,
        solicitud_id=solicitud_id,
        persona_id=persona_id,
        fecha_raw=fecha_raw,
        desde_raw=desde_raw,
        hasta_raw=hasta_raw,
        delegada_raw=delegada_raw,
    )


@pytest.mark.parametrize(
    ("fecha_raw", "desde_raw", "hasta_raw", "delegada_raw", "expected_fecha", "expected_desde", "expected_hasta", "expected_delegada"),
    [
        ("2026-01-01", "08:00", "10:00", "Ana", "2026-01-01", "08:00", "10:00", "Ana"),
        (None, "08:00", "10:00", "Ana", "", "08:00", "10:00", "Ana"),
        ("-", "08:00", "10:00", "Ana", "", "08:00", "10:00", "Ana"),
        ("2026-01-01", None, "10:00", "Ana", "2026-01-01", "", "10:00", "Ana"),
        ("2026-01-01", "-", "10:00", "Ana", "2026-01-01", "", "10:00", "Ana"),
        ("2026-01-01", "08:00", None, "Ana", "2026-01-01", "08:00", "", "Ana"),
        ("2026-01-01", "08:00", "-", "Ana", "2026-01-01", "08:00", "", "Ana"),
        ("2026-01-01", "08:00", "10:00", None, "2026-01-01", "08:00", "10:00", None),
        ("2026-01-01", "08:00", "10:00", "-", "2026-01-01", "08:00", "10:00", None),
        (123, 800, 1000, 0, "123", "800", "1000", 0),
        ("", "", "", "", "", "", "", ""),
        ("2026-12-24", "23:59", "00:00", "María", "2026-12-24", "23:59", "00:00", "María"),
    ],
)
def test_plan_iter_pendientes_normaliza_campos(
    fecha_raw,
    desde_raw,
    hasta_raw,
    delegada_raw,
    expected_fecha,
    expected_desde,
    expected_hasta,
    expected_delegada,
) -> None:
    plan = plan_iter_pendientes(IterPendientesEntrada(ui_ready=True, rows=(_row(0, fecha_raw=fecha_raw, desde_raw=desde_raw, hasta_raw=hasta_raw, delegada_raw=delegada_raw),)))

    assert plan.reason_code == "rows_planned"
    assert len(plan.actions) == 1
    action = plan.actions[0]
    assert action.reason_code == "row_included"
    assert action.payload["fecha"] == expected_fecha
    assert action.payload["desde"] == expected_desde
    assert action.payload["hasta"] == expected_hasta
    assert action.payload["delegada"] == expected_delegada


@pytest.mark.parametrize(
    ("rows", "expected_rows"),
    [
        ((_row(0),), [0]),
        ((_row(0), _row(1)), [0, 1]),
        ((_row(2), _row(5), _row(9)), [2, 5, 9]),
        ((_row(3, solicitud_id=None), _row(4, persona_id=None)), [3, 4]),
        ((_row(7, delegada_raw=None),), [7]),
        ((_row(8, fecha_raw=None), _row(10, desde_raw="-")), [8, 10]),
        ((_row(11, hasta_raw="-"), _row(12, delegada_raw="-"), _row(13)), [11, 12, 13]),
        ((_row(1), _row(-1), _row(2)), [1, 2]),
        ((_row(-2), _row(-1), _row(0)), [0]),
        ((_row(20), _row(21), _row(22), _row(23)), [20, 21, 22, 23]),
        ((_row(30, solicitud_id=1), _row(31, solicitud_id=2), _row(32, solicitud_id=3)), [30, 31, 32]),
        ((_row(40, persona_id=1), _row(41, persona_id=2), _row(42, persona_id=3)), [40, 41, 42]),
        ((_row(50, fecha_raw="-"), _row(51, fecha_raw=None), _row(52, fecha_raw="ok")), [50, 51, 52]),
        ((_row(60, desde_raw="-"), _row(61, desde_raw=None), _row(62, desde_raw="ok")), [60, 61, 62]),
        ((_row(70, hasta_raw="-"), _row(71, hasta_raw=None), _row(72, hasta_raw="ok")), [70, 71, 72]),
        ((_row(80, delegada_raw="-"), _row(81, delegada_raw=None), _row(82, delegada_raw="ok")), [80, 81, 82]),
        ((_row(90, fecha_raw=0), _row(91, desde_raw=0), _row(92, hasta_raw=0)), [90, 91, 92]),
        ((_row(100, solicitud_id=None), _row(-100), _row(101, solicitud_id=None)), [100, 101]),
        ((_row(110, persona_id=None), _row(111, persona_id=None), _row(-111)), [110, 111]),
        ((_row(120, delegada_raw=0), _row(121, delegada_raw=False), _row(122, delegada_raw="-")), [120, 121, 122]),
        ((_row(130, fecha_raw="-", desde_raw="-", hasta_raw="-"), _row(131), _row(-131)), [130, 131]),
        ((), []),
        ((_row(-3), _row(-2), _row(-1)), []),
    ],
)
def test_plan_iter_pendientes_ordena_y_filtra_rows(rows, expected_rows) -> None:
    plan = plan_iter_pendientes(IterPendientesEntrada(ui_ready=True, rows=rows))

    if expected_rows:
        assert plan.reason_code == "rows_planned"
    else:
        assert plan.reason_code == "no_rows_to_iterate"
    assert [action.payload["row"] for action in plan.actions] == expected_rows


def test_precedencia_ui_not_ready_es_first_match() -> None:
    plan = plan_iter_pendientes(IterPendientesEntrada(ui_ready=False, rows=(_row(0), _row(1), _row(-1))))

    assert plan.reason_code == "ui_not_ready"
    assert plan.actions == ()


def test_contrato_reason_code_criticos() -> None:
    assert plan_iter_pendientes(IterPendientesEntrada(ui_ready=False, rows=(_row(0),))).reason_code == "ui_not_ready"
    assert plan_iter_pendientes(IterPendientesEntrada(ui_ready=True, rows=())).reason_code == "no_rows_to_iterate"
    assert plan_iter_pendientes(IterPendientesEntrada(ui_ready=True, rows=(_row(-1),))).reason_code == "no_rows_to_iterate"

    planned = plan_iter_pendientes(IterPendientesEntrada(ui_ready=True, rows=(_row(0),)))
    assert planned.reason_code == "rows_planned"
    assert planned.actions[0].reason_code == "row_included"

    planned_none = plan_iter_pendientes(IterPendientesEntrada(ui_ready=True, rows=(_row(1, solicitud_id=None, persona_id=None),)))
    assert planned_none.reason_code == "rows_planned"
    assert planned_none.actions[0].reason_code == "row_included"


def test_contrato_sin_side_effects_si_no_procede() -> None:
    plan_empty = plan_iter_pendientes(IterPendientesEntrada(ui_ready=True, rows=()))
    plan_invalid_rows = plan_iter_pendientes(IterPendientesEntrada(ui_ready=True, rows=(_row(-1), _row(-2))))
    plan_ui_off = plan_iter_pendientes(IterPendientesEntrada(ui_ready=False, rows=(_row(0),)))

    assert plan_empty.actions == ()
    assert plan_invalid_rows.actions == ()
    assert plan_ui_off.actions == ()
