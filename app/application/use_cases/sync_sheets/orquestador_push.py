from __future__ import annotations

from app.application.sheets_service import SHEETS_SCHEMA
from typing import Any

from app.application.use_cases.sync_sheets.ayudantes_push import push_config, push_delegadas, push_pdf_log
from app.application.use_cases.sync_sheets import persistence_ops
from app.application.use_cases.sync_sheets.helpers import build_solicitudes_sync_plan
from app.application.use_cases.sync_sheets.persona_resolution_rules import build_persona_resolution_plan
from app.application.use_cases.sync_sheets.orquestacion_modelos import HEADER_CANONICO_SOLICITUDES
from app.application.use_cases.sync_sheets.sync_snapshots import build_local_solicitud_payload
from app.application.use_cases.sync_sheets import payloads_puros
from app.application.use_cases import sync_sheets_core
from app.domain.sync_models import SyncExecutionPlan, SyncSummary
import logging

logger = logging.getLogger(__name__)


class OrquestadorPushSheets:
        def __getattr__(self, name: str) -> Any:
            raise AttributeError(name)

        def _push_with_spreadsheet(self, spreadsheet: Any) -> SyncSummary:
            self._reset_write_batch_state()
            write_calls_before = self._client.get_write_calls_count() if hasattr(self._client, "get_write_calls_count") else 0
            last_sync_at = self._get_last_sync_at()
            uploaded = 0
            conflicts = 0
            omitted_duplicates = 0
            self._sync_local_cuadrantes_from_personas()
            uploaded_count, conflict_count = self._push_delegadas(spreadsheet, last_sync_at)
            uploaded += uploaded_count
            conflicts += conflict_count
            uploaded_count, conflict_count, duplicate_count = self._push_solicitudes(spreadsheet, last_sync_at)
            uploaded += uploaded_count
            conflicts += conflict_count
            omitted_duplicates += duplicate_count
            uploaded_count, conflict_count = self._push_cuadrantes(spreadsheet, last_sync_at)
            uploaded += uploaded_count
            conflicts += conflict_count
            uploaded += self._push_pdf_log(spreadsheet, last_sync_at)
            uploaded += self._push_config(spreadsheet, last_sync_at)
            self._set_last_sync_at(self._now_iso())
            write_calls_after = self._client.get_write_calls_count() if hasattr(self._client, "get_write_calls_count") else 0
            logger.info("Write calls por sync (push): %s", write_calls_after - write_calls_before)
            return SyncSummary(
                inserted_remote=uploaded,
                updated_remote=0,
                duplicates_skipped=omitted_duplicates,
                conflicts_detected=conflicts,
            )

        def _push_pdf_log(self, spreadsheet: Any, last_sync_at: str | None) -> int:
            return push_pdf_log(self, spreadsheet, last_sync_at)

        def _push_config(self, spreadsheet: Any, last_sync_at: str | None) -> int:
            return push_config(self, spreadsheet, last_sync_at)

        def _push_delegadas(self, spreadsheet: Any, last_sync_at: str | None) -> tuple[int, int]:
            return push_delegadas(self, spreadsheet, last_sync_at)

        def _push_solicitudes(self, spreadsheet: Any, last_sync_at: str | None) -> tuple[int, int, int]:
            worksheet = self._get_worksheet(spreadsheet, "solicitudes")
            headers, rows = self._rows_with_index(worksheet)
            remote_index = self._uuid_index(rows)
            cursor = self._connection.cursor()
            cursor.execute(
                """
                SELECT s.id, s.uuid, s.persona_id, s.fecha_pedida, s.desde_min, s.hasta_min,
                       s.completo, s.horas_solicitadas_min, s.notas, s.created_at, s.updated_at,
                       s.source_device, s.deleted, s.pdf_hash,
                       p.uuid AS delegada_uuid, p.nombre AS delegada_nombre
                FROM solicitudes s
                JOIN personas p ON p.id = s.persona_id
                WHERE s.updated_at IS NOT NULL
                """
            )
            import app.application.use_cases.sync_sheets.use_case as uc
            result = uc.build_push_solicitudes_payloads(
                header=tuple(HEADER_CANONICO_SOLICITUDES),
                local_rows=cursor.fetchall(),
                remote_rows=rows,
                remote_index=remote_index,
                last_sync_at=last_sync_at,
                local_payload_builder=self._local_solicitud_payload,
                remote_payload_builder=self._remote_solicitud_payload,
            )
            for conflict in result.conflicts:
                self._store_conflict("solicitudes", conflict.uuid_value, conflict.local_row, conflict.remote_row)

            if headers != HEADER_CANONICO_SOLICITUDES:
                logger.info("Reescribiendo encabezado canónico de 'solicitudes' (sin columnas extras o vacías).")
                self._normalize_solicitudes_header(worksheet)

            uc.run_push_values_update(worksheet, result.values, retries=2)
            logger.info("PUSH Sheets: %s filas enviadas", max(len(result.values) - 1, 0))
            return result.uploaded, len(result.conflicts), result.omitted_duplicates

        def _build_solicitudes_sync_plan(self, spreadsheet: Any) -> SyncExecutionPlan:
            return build_solicitudes_sync_plan(self, spreadsheet, HEADER_CANONICO_SOLICITUDES)

        def _local_solicitud_payload(self, row: Any) -> tuple[Any, ...]:
            fallback_device_id = row["source_device"] or self._device_id()
            return build_local_solicitud_payload(
                row,
                device_id=fallback_device_id,
                to_iso_date=sync_sheets_core.to_iso_date,
                split_minutes=sync_sheets_core.split_minutes,
                int_or_zero=sync_sheets_core.int_or_zero,
            )

        def _remote_solicitud_payload(self, remote_row: dict[str, Any]) -> tuple[Any, ...]:
            return payloads_puros.payload_remoto_solicitud(remote_row)

        def _push_cuadrantes(self, spreadsheet: Any, last_sync_at: str | None) -> tuple[int, int]:
            worksheet = self._get_worksheet(spreadsheet, "cuadrantes")
            headers, rows = self._rows_with_index(worksheet)
            header_map = self._header_map(headers, SHEETS_SCHEMA["cuadrantes"])
            remote_index = self._uuid_index(rows)
            cursor = self._connection.cursor()
            cursor.execute(
                """
                SELECT id, uuid, delegada_uuid, dia_semana, man_min, tar_min, updated_at, source_device, deleted
                FROM cuadrantes
                WHERE updated_at IS NOT NULL
                """
            )
            uploaded = 0
            conflicts = 0
            for row in cursor.fetchall():
                if not sync_sheets_core.is_after_last_sync(row["updated_at"], last_sync_at):
                    continue
                uuid_value = row["uuid"]
                remote_row = remote_index.get(uuid_value)
                remote_updated_at = sync_sheets_core.parse_iso(remote_row.get("updated_at") if remote_row else None)
                if sync_sheets_core.is_conflict(row["updated_at"], remote_updated_at, last_sync_at):
                    self._store_conflict("cuadrantes", uuid_value, dict(row), remote_row or {})
                    conflicts += 1
                    continue
                man_h, man_m = sync_sheets_core.split_minutes(row["man_min"])
                tar_h, tar_m = sync_sheets_core.split_minutes(row["tar_min"])
                payload = {
                    "uuid": uuid_value,
                    "delegada_uuid": row["delegada_uuid"],
                    "dia_semana": row["dia_semana"],
                    "man_h": man_h,
                    "man_m": man_m,
                    "tar_h": tar_h,
                    "tar_m": tar_m,
                    "updated_at": row["updated_at"],
                    "source_device": row["source_device"] or self._device_id(),
                    "deleted": row["deleted"] or 0,
                }
                if remote_row:
                    if self._enable_backfill:
                        row_number = remote_row["__row_number__"]
                        self._update_row(worksheet, row_number, header_map, payload)
                    continue
                self._append_row(worksheet, header_map, payload)
                uploaded += 1
            self._flush_write_batches(spreadsheet, worksheet)
            return uploaded, conflicts

        def _fetch_persona(self, uuid_value: str) -> Any | None:
            cursor = self._connection.cursor()
            cursor.execute(
                """
                SELECT id, uuid, nombre, genero, is_active, horas_mes_min, horas_ano_min,
                       updated_at, source_device, deleted,
                       cuad_lun_man_min, cuad_lun_tar_min, cuad_mar_man_min, cuad_mar_tar_min,
                       cuad_mie_man_min, cuad_mie_tar_min, cuad_jue_man_min, cuad_jue_tar_min,
                       cuad_vie_man_min, cuad_vie_tar_min, cuad_sab_man_min, cuad_sab_tar_min,
                       cuad_dom_man_min, cuad_dom_tar_min
                FROM personas
                WHERE uuid = ?
                """,
                (uuid_value,),
            )
            return cursor.fetchone()

        def _fetch_persona_by_nombre(self, nombre: str) -> Any | None:
            cursor = self._connection.cursor()
            cursor.execute(
                """
                SELECT id, uuid, nombre, genero, is_active, horas_mes_min, horas_ano_min,
                       updated_at, source_device, deleted,
                       cuad_lun_man_min, cuad_lun_tar_min, cuad_mar_man_min, cuad_mar_tar_min,
                       cuad_mie_man_min, cuad_mie_tar_min, cuad_jue_man_min, cuad_jue_tar_min,
                       cuad_vie_man_min, cuad_vie_tar_min, cuad_sab_man_min, cuad_sab_tar_min,
                       cuad_dom_man_min, cuad_dom_tar_min
                FROM personas
                WHERE nombre = ?
                """,
                (nombre,),
            )
            return cursor.fetchone()

        def _get_or_create_persona(self, row: dict[str, Any]) -> tuple[Any | None, bool, str | None]:
            persona_uuid = payloads_puros.uuid_o_none(row.get("uuid"))
            nombre = payloads_puros.valor_normalizado(row.get("nombre"))
            by_uuid = self._fetch_persona(persona_uuid) if persona_uuid else None
            by_nombre = self._fetch_persona_by_nombre(nombre) if nombre else None
            plan = build_persona_resolution_plan(persona_uuid, nombre, by_uuid, by_nombre)
            return self._apply_persona_resolution(plan, row, nombre)

        def _apply_persona_resolution(
            self,
            plan: dict[str, Any],
            row: dict[str, Any],
            nombre: str,
        ) -> tuple[Any | None, bool, str | None]:
            accion = plan["accion"]
            if accion == "usar_uuid":
                return self._persona_result(self._fetch_persona(plan["uuid"]), False)
            if accion in {"usar_nombre", "colision_nombre"}:
                if accion == "colision_nombre":
                    logger.warning(
                        "Colisión persona por nombre; se prioriza existente. nombre=%s uuid_local=%s uuid_remoto=%s",
                        plan.get("nombre"),
                        plan.get("uuid"),
                        payloads_puros.valor_normalizado(row.get("uuid")),
                    )
                return self._persona_result(self._fetch_persona_by_nombre(nombre), False)
            if accion == "asignar_uuid_por_nombre":
                self._assign_uuid_to_persona(plan["id"], plan["uuid"], row)
                return self._persona_result(self._fetch_persona(plan["uuid"]) or self._fetch_persona_by_nombre(nombre), False)
            target_uuid = plan["uuid"] or self._generate_uuid()
            logger.info("Insertando persona nueva: uuid=%s, nombre=%s", target_uuid, nombre)
            self._insert_persona_from_remote(target_uuid, row)
            return self._persona_result(self._fetch_persona(target_uuid), True)

        def _persona_result(self, persona: Any | None, was_inserted: bool) -> tuple[Any | None, bool, str | None]:
            if persona is not None:
                logger.info("Persona existente: uuid=%s, nombre=%s", persona["uuid"], persona["nombre"])
                return persona, was_inserted, persona["uuid"]
            return None, was_inserted, None

        def _assign_uuid_to_persona(self, persona_id: int, persona_uuid: str, row: dict[str, Any]) -> None:
            fixed_now = row.get("updated_at") or self._now_iso()
            persistence_ops.backfill_uuid(self._connection, "personas", persona_id, persona_uuid, lambda: fixed_now)
            self._connection.commit()

        def _ejecutar_insert_remoto_solicitud(self, payload: tuple[Any, ...]) -> None:
            persistence_ops.execute_insert_solicitud(self._connection, payload)

        def _ejecutar_update_remoto_solicitud(self, payload: tuple[Any, ...]) -> None:
            persistence_ops.execute_update_solicitud(self._connection, payload)

        def _normalize_solicitudes_header(self, worksheet: Any) -> None:
            worksheet.update("A1", [HEADER_CANONICO_SOLICITUDES])
            try:
                worksheet.resize(cols=len(HEADER_CANONICO_SOLICITUDES))
            except OSError:
                logger.debug("No se pudo ajustar columnas de la worksheet 'solicitudes'.", exc_info=True)
