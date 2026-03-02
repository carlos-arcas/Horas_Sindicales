from __future__ import annotations

from typing import Any

from app.application.use_cases import sync_sheets_core
from app.application.use_cases.sync_sheets import persistence_ops
from app.application.use_cases.sync_sheets.helpers import (
    calcular_bloque_horario_solicitud,
    construir_payload_actualizacion_solicitud,
    construir_payload_insercion_solicitud,
    extraer_datos_delegada,
    normalizar_fechas_solicitud,
)
from app.application.sheets_service import SHEETS_SCHEMA

from app.application.use_cases.sync_sheets.sync_sheets_helpers import execute_with_validation, rows_with_index
from app.domain.sheets_errors import SheetsRateLimitError
import logging

logger = logging.getLogger(__name__)


class OrquestadorPersistenciaSync:
        def _find_solicitud_by_composite_key(self, row: dict[str, Any]) -> Any | None:
            delegada_uuid = str(row.get("delegada_uuid", "")).strip() or None
            persona_id = self._persona_id_from_uuid(delegada_uuid)
            return persistence_ops.find_solicitud_by_composite_key(self._connection, row, persona_id)

        def _backfill_uuid(self, worksheet: Any, headers: list[str], row_number: int, column: str, value: str) -> None:
            if not self._enable_backfill or not value:
                return
            if column not in headers:
                return
            col_idx = headers.index(column) + 1
            # Evita write-per-row: acumulamos backfills y se ejecutan en un único values_batch_update por worksheet.
            self._queue_values_batch_update(worksheet, row_number, col_idx, value)

        def _fetch_solicitud(self, uuid_value: str) -> Any | None:
            cursor = self._connection.cursor()
            cursor.execute(
                """
                SELECT id, uuid, persona_id, fecha_pedida, desde_min, hasta_min, completo,
                       horas_solicitadas_min, notas, created_at, updated_at, source_device, deleted, pdf_hash
                FROM solicitudes
                WHERE uuid = ?
                """,
                (uuid_value,),
            )
            return cursor.fetchone()

        def _fetch_cuadrante(self, uuid_value: str) -> Any | None:
            cursor = self._connection.cursor()
            cursor.execute(
                """
                SELECT id, uuid, delegada_uuid, dia_semana, man_min, tar_min, updated_at, source_device, deleted
                FROM cuadrantes
                WHERE uuid = ?
                """,
                (uuid_value,),
            )
            return cursor.fetchone()

        def _insert_persona_from_remote(self, uuid_value: str, row: dict[str, Any]) -> None:
            persistence_ops.insert_persona_from_remote(self._connection, uuid_value, row, self._now_iso)
            self._connection.commit()

        def _update_persona_from_remote(self, persona_id: int, row: dict[str, Any]) -> None:
            persistence_ops.update_persona_from_remote(self._connection, persona_id, row, self._now_iso)
            self._connection.commit()

        def _insert_solicitud_from_remote(self, uuid_value: str, row: dict[str, Any]) -> tuple[bool, int, int]:
            persona_id = self._resolver_persona_para_solicitud(row, uuid_value)
            if persona_id is None:
                return False, 1, 1
            fecha_normalizada, created_normalizada = normalizar_fechas_solicitud(row, sync_sheets_core.normalize_date)
            if not fecha_normalizada:
                logger.warning("Solicitud %s descartada por fecha inválida en pull: %s", uuid_value, row.get("fecha"))
                return False, 0, 1
            desde_min, hasta_min = calcular_bloque_horario_solicitud(row, sync_sheets_core.join_minutes)
            payload = construir_payload_insercion_solicitud(
                uuid_value,
                persona_id,
                row,
                fecha_normalizada,
                created_normalizada,
                desde_min,
                hasta_min,
                sync_sheets_core.int_or_zero,
                self._now_iso,
            )
            self._ejecutar_insert_remoto_solicitud(payload)
            if not self._defer_local_commits:
                self._connection.commit()
            logger.info("Solicitud importada a tabla local 'solicitudes' (histórico): uuid=%s", uuid_value)
            return True, 0, 0

        def _update_solicitud_from_remote(self, solicitud_id: int, row: dict[str, Any]) -> tuple[bool, int, int]:
            identificador = str(row.get("uuid") or solicitud_id)
            persona_id = self._resolver_persona_para_solicitud(row, identificador)
            if persona_id is None:
                return False, 1, 1
            fecha_normalizada, created_normalizada = normalizar_fechas_solicitud(row, sync_sheets_core.normalize_date)
            if not fecha_normalizada:
                logger.warning("Solicitud id=%s no actualizada por fecha inválida en pull: %s", solicitud_id, row.get("fecha"))
                return False, 0, 1
            desde_min, hasta_min = calcular_bloque_horario_solicitud(row, sync_sheets_core.join_minutes)
            payload = construir_payload_actualizacion_solicitud(
                solicitud_id,
                persona_id,
                row,
                fecha_normalizada,
                created_normalizada,
                desde_min,
                hasta_min,
                sync_sheets_core.int_or_zero,
                self._now_iso,
            )
            self._ejecutar_update_remoto_solicitud(payload)
            if not self._defer_local_commits:
                self._connection.commit()
            return True, 0, 0

        def _resolver_persona_para_solicitud(self, row: dict[str, Any], identificador: str) -> int | None:
            delegada_uuid, delegada_nombre = extraer_datos_delegada(row)
            if not delegada_uuid:
                logger.warning(
                    "Solicitud %s sin delegada_uuid, resolviendo por nombre '%s'",
                    identificador,
                    delegada_nombre,
                )
            import app.application.use_cases.sync_sheets.use_case as uc
            resolved_uuid = uc.get_or_resolve_delegada_uuid(self._connection, delegada_uuid, delegada_nombre)
            if not resolved_uuid:
                logger.warning("Solicitud omitida por delegada no resuelta: %s", identificador)
                return None
            persona_id = self._persona_id_from_uuid(resolved_uuid)
            if persona_id is None:
                logger.warning("Solicitud omitida por delegada no resuelta: %s", identificador)
                return None
            logger.info("Delegada resuelta: %s %s", resolved_uuid, delegada_nombre)
            return persona_id

        def _insert_cuadrante_from_remote(self, uuid_value: str, row: dict[str, Any]) -> None:
            cursor = self._connection.cursor()
            cursor.execute(
                """
                INSERT INTO cuadrantes (
                    uuid, delegada_uuid, dia_semana, man_min, tar_min, updated_at, source_device, deleted
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    uuid_value,
                    row.get("delegada_uuid"),
                    row.get("dia_semana"),
                    sync_sheets_core.join_minutes(row.get("man_h"), row.get("man_m")),
                    sync_sheets_core.join_minutes(row.get("tar_h"), row.get("tar_m")),
                    row.get("updated_at") or self._now_iso(),
                    row.get("source_device"),
                    sync_sheets_core.int_or_zero(row.get("deleted")),
                ),
            )
            self._connection.commit()
            self._apply_cuadrante_to_persona(row)

        def _update_cuadrante_from_remote(self, cuadrante_id: int, row: dict[str, Any]) -> None:
            cursor = self._connection.cursor()
            cursor.execute(
                """
                UPDATE cuadrantes
                SET delegada_uuid = ?, dia_semana = ?, man_min = ?, tar_min = ?, updated_at = ?, source_device = ?, deleted = ?
                WHERE id = ?
                """,
                (
                    row.get("delegada_uuid"),
                    row.get("dia_semana"),
                    sync_sheets_core.join_minutes(row.get("man_h"), row.get("man_m")),
                    sync_sheets_core.join_minutes(row.get("tar_h"), row.get("tar_m")),
                    row.get("updated_at") or self._now_iso(),
                    row.get("source_device"),
                    sync_sheets_core.int_or_zero(row.get("deleted")),
                    cuadrante_id,
                ),
            )
            self._connection.commit()
            self._apply_cuadrante_to_persona(row)

        def _apply_cuadrante_to_persona(self, row: dict[str, Any]) -> None:
            delegada_uuid = row.get("delegada_uuid")
            dia = normalize_dia(str(row.get("dia_semana", "")))
            if not delegada_uuid or not dia:
                return
            persona_id = self._persona_id_from_uuid(delegada_uuid)
            if persona_id is None:
                return
            man_min = sync_sheets_core.join_minutes(row.get("man_h"), row.get("man_m"))
            tar_min = sync_sheets_core.join_minutes(row.get("tar_h"), row.get("tar_m"))
            cursor = self._connection.cursor()
            sql = f"""
                UPDATE personas
                SET cuad_{dia}_man_min = ?, cuad_{dia}_tar_min = ?
                WHERE id = ?
                """
            execute_with_validation(cursor, sql, (man_min, tar_min, persona_id), "personas.update_cuadrante")
            self._connection.commit()

        def _persona_id_from_uuid(self, delegada_uuid: str | None) -> int | None:
            if not delegada_uuid:
                return None
            cursor = self._connection.cursor()
            cursor.execute("SELECT id FROM personas WHERE uuid = ?", (delegada_uuid,))
            row = cursor.fetchone()
            if not row:
                return None
            return row["id"]

        def _store_conflict(
            self, entity_type: str, uuid_value: str, local_snapshot: dict[str, Any], remote_snapshot: dict[str, Any]
        ) -> None:
            persistence_ops.store_conflict(self._connection, uuid_value, entity_type, local_snapshot, remote_snapshot, self._now_iso)
            if not self._defer_local_commits:
                self._connection.commit()

        def _rows_with_index(
            self,
            worksheet: Any,
            worksheet_name: str | None = None,
            aliases: dict[str, list[str]] | None = None,
        ) -> tuple[list[str], list[tuple[int, dict[str, Any]]]]:
            cache_name = worksheet_name or getattr(worksheet, "title", None)
            if cache_name:
                try:
                    values = self._client.read_all_values(cache_name)
                except SheetsRateLimitError:
                    logger.warning("Rate limit al leer worksheet=%s; reintentando una vez.", cache_name)
                    values = self._client.read_all_values(cache_name)
                self._servicio_escritura_lotes.registrar_siguiente_fila_append(cache_name, len(values))
            else:
                values = worksheet.get_all_values()
            return rows_with_index(values, worksheet_name=cache_name or worksheet.title, aliases=aliases)

        def _header_map(self, headers: list[str], expected: list[str]) -> list[str]:
            if not headers:
                return expected
            missing = [col for col in expected if col not in headers]
            return headers + missing

        def _uuid_index(self, rows: list[tuple[int, dict[str, Any]]]) -> dict[str, dict[str, Any]]:
            index: dict[str, dict[str, Any]] = {}
            for _, row in rows:
                uuid_value = str(row.get("uuid", "")).strip()
                if uuid_value:
                    index[uuid_value] = row
            return index

        def _update_row(self, worksheet: Any, row_number: int, headers: list[str], payload: dict[str, Any]) -> None:
            self._servicio_escritura_lotes.encolar_actualizacion(worksheet, row_number, headers, payload)

        def _append_row(self, worksheet: Any, headers: list[str], payload: dict[str, Any]) -> None:
            self._servicio_escritura_lotes.encolar_alta(worksheet, headers, payload)

        def _reset_write_batch_state(self) -> None:
            self._servicio_escritura_lotes.reiniciar()

        def _queue_values_batch_update(self, worksheet: Any, row_number: int, col_idx: int, value: Any) -> None:
            self._servicio_escritura_lotes.encolar_backfill(worksheet, row_number, col_idx, value)

        def _flush_write_batches(self, spreadsheet: Any, worksheet: Any) -> None:
            self._servicio_escritura_lotes.flush(
                spreadsheet=spreadsheet,
                worksheet=worksheet,
                cliente=self._client,
                lector_valores=self._client.read_all_values,
            )

        @staticmethod
        def _solicitud_dedupe_key_from_remote_row(row: dict[str, Any]) -> tuple[object, ...] | None:
            return sync_sheets_core.solicitud_dedupe_key_from_remote_row(row)

        @staticmethod
        def _solicitud_dedupe_key_from_local_row(row: dict[str, Any]) -> tuple[object, ...] | None:
            return sync_sheets_core.solicitud_dedupe_key_from_local_row(row)

        def _is_duplicate_local_solicitud(self, key: tuple[object, ...], exclude_uuid: str | None = None) -> bool:
            return persistence_ops.is_duplicate_local_solicitud(self._connection, key, exclude_uuid)
