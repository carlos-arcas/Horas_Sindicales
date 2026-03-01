from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable

from app.application.use_cases.sync_sheets.sync_sheets_helpers import rowcol_to_a1


logger = logging.getLogger(__name__)


@dataclass
class EstadoEscrituraLotes:
    pendientes_altas: dict[str, list[list[Any]]] = field(default_factory=dict)
    pendientes_actualizaciones: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    pendientes_backfill: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    siguiente_fila_append: dict[str, int] = field(default_factory=dict)


class ServicioEscrituraLotes:
    def __init__(self) -> None:
        self._estado = EstadoEscrituraLotes()

    @property
    def pendientes_altas(self) -> dict[str, list[list[Any]]]:
        return self._estado.pendientes_altas

    @property
    def pendientes_actualizaciones(self) -> dict[str, list[dict[str, Any]]]:
        return self._estado.pendientes_actualizaciones

    @property
    def pendientes_backfill(self) -> dict[str, list[dict[str, Any]]]:
        return self._estado.pendientes_backfill

    @property
    def siguiente_fila_append(self) -> dict[str, int]:
        return self._estado.siguiente_fila_append

    def reiniciar(self) -> None:
        self._estado.pendientes_altas.clear()
        self._estado.pendientes_actualizaciones.clear()
        self._estado.pendientes_backfill.clear()
        self._estado.siguiente_fila_append.clear()

    def registrar_siguiente_fila_append(self, hoja: str, total_valores: int) -> None:
        self._estado.siguiente_fila_append[hoja] = total_valores + 1

    def encolar_actualizacion(self, worksheet: Any, fila: int, cabeceras: list[str], payload: dict[str, Any]) -> None:
        valores = [payload.get(cabecera, "") for cabecera in cabeceras]
        rango = f"A{fila}:{rowcol_to_a1(fila, len(cabeceras))}"
        self._estado.pendientes_actualizaciones.setdefault(worksheet.title, []).append({"range": rango, "values": [valores]})

    def encolar_alta(self, worksheet: Any, cabeceras: list[str], payload: dict[str, Any]) -> None:
        valores = [payload.get(cabecera, "") for cabecera in cabeceras]
        self._estado.pendientes_altas.setdefault(worksheet.title, []).append(valores)

    def encolar_backfill(self, worksheet: Any, fila: int, columna: int, valor: Any) -> None:
        celda = rowcol_to_a1(fila, columna)
        titulo = worksheet.title.replace("'", "''")
        rango = f"'{titulo}'!{celda}"
        entrada = {"range": rango, "values": [[valor]]}
        self._estado.pendientes_backfill.setdefault(worksheet.title, []).append(entrada)

    def flush(
        self,
        *,
        spreadsheet: Any,
        worksheet: Any,
        cliente: Any,
        lector_valores: Callable[[str], list[list[Any]]],
    ) -> None:
        titulo = worksheet.title
        altas = self._estado.pendientes_altas.pop(titulo, [])
        actualizaciones = self._estado.pendientes_actualizaciones.pop(titulo, [])
        backfills = self._estado.pendientes_backfill.pop(titulo, [])
        altas_en_rango = self._build_append_batch_entries(
            worksheet=worksheet,
            filas=altas,
            lector_valores=lector_valores,
        )
        body = self._compose_values_batch_body(altas_en_rango, actualizaciones, backfills)
        self._write_batch(body=body, cliente=cliente, spreadsheet=spreadsheet)
        self._log_write_batch(
            titulo=titulo,
            altas=altas,
            actualizaciones=actualizaciones,
            backfills=backfills,
            total_rangos=len(body["data"]),
        )

    def _build_append_batch_entries(
        self,
        *,
        worksheet: Any,
        filas: list[list[Any]],
        lector_valores: Callable[[str], list[list[Any]]],
    ) -> list[dict[str, Any]]:
        if not filas:
            return []
        titulo = worksheet.title
        fila_inicio = self._estado.siguiente_fila_append.get(titulo)
        if fila_inicio is None:
            fila_inicio = len(lector_valores(titulo)) + 1
        total_columnas = len(filas[0]) if filas[0] else 1
        rango = self._a1_sheet_range(titulo, fila_inicio, total_columnas, len(filas))
        self._estado.siguiente_fila_append[titulo] = fila_inicio + len(filas)
        return [{"range": rango, "values": filas}]

    @staticmethod
    def _a1_sheet_range(titulo: str, fila_inicio: int, total_columnas: int, total_filas: int = 1) -> str:
        titulo_escapado = titulo.replace("'", "''")
        fila_fin = fila_inicio + max(total_filas, 1) - 1
        col_fin = rowcol_to_a1(1, total_columnas).rstrip("1")
        return f"'{titulo_escapado}'!A{fila_inicio}:{col_fin}{fila_fin}"

    @staticmethod
    def _compose_values_batch_body(*partes: list[dict[str, Any]]) -> dict[str, Any]:
        data = [entrada for parte in partes for entrada in parte]
        return {"valueInputOption": "USER_ENTERED", "data": data}

    @staticmethod
    def _write_batch(*, body: dict[str, Any], cliente: Any, spreadsheet: Any) -> None:
        if not body["data"]:
            return
        if hasattr(cliente, "values_batch_update"):
            cliente.values_batch_update(body)
            return
        spreadsheet.values_batch_update(body)

    @staticmethod
    def _log_write_batch(
        *,
        titulo: str,
        altas: list[list[Any]],
        actualizaciones: list[dict[str, Any]],
        backfills: list[dict[str, Any]],
        total_rangos: int,
    ) -> None:
        if not (altas or actualizaciones or backfills):
            return
        logger.info(
            "Write batch (%s): appended=%s updated=%s backfills=%s total_ranges=%s",
            titulo,
            len(altas),
            len(actualizaciones),
            len(backfills),
            total_rangos,
        )
