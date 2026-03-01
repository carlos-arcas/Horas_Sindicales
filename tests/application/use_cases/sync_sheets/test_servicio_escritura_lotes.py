from __future__ import annotations

from unittest.mock import Mock

import pytest

from app.application.use_cases.sync_sheets.servicio_escritura_lotes import ServicioEscrituraLotes


class _FakeWorksheet:
    def __init__(self, title: str) -> None:
        self.title = title


class _FakeSpreadsheet:
    def __init__(self) -> None:
        self.values_batch_update = Mock()


class _FakeCliente:
    def __init__(self) -> None:
        self.values_batch_update = Mock()
        self.read_all_values = Mock(return_value=[["uuid", "nombre"]])


def test_flush_escribe_lotes_esperados() -> None:
    servicio = ServicioEscrituraLotes()
    cliente = _FakeCliente()
    spreadsheet = _FakeSpreadsheet()
    worksheet = _FakeWorksheet("solicitudes")

    servicio.encolar_alta(worksheet, ["uuid", "estado"], {"uuid": "uuid-1", "estado": "A"})
    servicio.encolar_actualizacion(worksheet, 2, ["uuid", "estado"], {"uuid": "uuid-1", "estado": "B"})
    servicio.encolar_backfill(worksheet, 3, 2, "ok")

    servicio.flush(
        spreadsheet=spreadsheet,
        worksheet=worksheet,
        cliente=cliente,
        lector_valores=cliente.read_all_values,
    )

    cliente.values_batch_update.assert_called_once_with(
        {
            "valueInputOption": "USER_ENTERED",
            "data": [
                {"range": "'solicitudes'!A2:B2", "values": [["uuid-1", "A"]]},
                {"range": "A2:B2", "values": [["uuid-1", "B"]]},
                {"range": "'solicitudes'!B3", "values": [["ok"]]},
            ],
        }
    )


def test_flush_propaga_excepcion_del_cliente() -> None:
    servicio = ServicioEscrituraLotes()
    cliente = _FakeCliente()
    worksheet = _FakeWorksheet("delegadas")
    spreadsheet = _FakeSpreadsheet()
    cliente.values_batch_update.side_effect = RuntimeError("fallo remoto")
    servicio.encolar_alta(worksheet, ["uuid"], {"uuid": "u-1"})

    with pytest.raises(RuntimeError, match="fallo remoto"):
        servicio.flush(
            spreadsheet=spreadsheet,
            worksheet=worksheet,
            cliente=cliente,
            lector_valores=cliente.read_all_values,
        )


def test_flush_sin_operaciones_no_escribe_ni_falla() -> None:
    servicio = ServicioEscrituraLotes()
    cliente = _FakeCliente()
    worksheet = _FakeWorksheet("delegadas")
    spreadsheet = _FakeSpreadsheet()

    servicio.flush(
        spreadsheet=spreadsheet,
        worksheet=worksheet,
        cliente=cliente,
        lector_valores=cliente.read_all_values,
    )

    cliente.values_batch_update.assert_not_called()
    spreadsheet.values_batch_update.assert_not_called()
