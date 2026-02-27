from __future__ import annotations

import sqlite3

import pytest

from app.application.use_cases.sync_sheets.sync_sheets_helpers import (
    execute_with_validation,
    rowcol_to_a1,
    rows_with_index,
)


def test_rowcol_to_a1_columnas_basicas_y_compuestas() -> None:
    assert rowcol_to_a1(1, 1) == "A1"
    assert rowcol_to_a1(3, 26) == "Z3"
    assert rowcol_to_a1(8, 27) == "AA8"


def test_execute_with_validation_ok() -> None:
    conn = sqlite3.connect(":memory:")
    cur = conn.cursor()
    execute_with_validation(cur, "SELECT ?", (1,), "ctx")


@pytest.mark.parametrize("sql,params", [("SELECT ?", ()), ("SELECT ? + ?", (1,))])
def test_execute_with_validation_mismatch(sql, params) -> None:
    conn = sqlite3.connect(":memory:")
    cur = conn.cursor()
    with pytest.raises(ValueError):
        execute_with_validation(cur, sql, params, "ctx-mismatch")


def test_rows_with_index_vacio() -> None:
    headers, rows = rows_with_index([], worksheet_name="ws")
    assert headers == []
    assert rows == []


def test_rows_with_index_omite_filas_en_blanco_y_mapea_aliases() -> None:
    values = [
        ["uuid", "Delegada", ""],
        ["u-1", "Ana", "x"],
        ["  ", "", ""],
        ["u-2", "", "x"],
    ]
    aliases = {"delegada_nombre": ["Delegada"]}
    headers, rows = rows_with_index(values, worksheet_name="ws", aliases=aliases)
    assert headers == ["uuid", "Delegada", ""]
    assert len(rows) == 2
    assert rows[0][1]["delegada_nombre"] == "Ana"
    assert rows[0][1]["__row_number__"] == 2


def test_rows_with_index_prioriza_valor_no_vacio_entre_aliases() -> None:
    values = [["Delegada", "delegada_nombre"], ["", "Marta"]]
    aliases = {"delegada_nombre": ["Delegada"]}
    _, rows = rows_with_index(values, worksheet_name="ws", aliases=aliases)
    assert rows[0][1]["delegada_nombre"] == "Marta"
