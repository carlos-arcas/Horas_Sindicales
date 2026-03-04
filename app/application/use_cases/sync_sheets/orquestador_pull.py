from __future__ import annotations

from typing import Any

from app.application.use_cases.sync_sheets.pull_planner import PullAction
from app.application.use_cases.sync_sheets.sync_snapshots import (
    PullContext,
    PullSignals,
    RemoteSolicitudRowDTO,
    build_pdf_log_payload,
    pdf_log_insert_values,
    pdf_log_update_values,
)
from app.application.use_cases.sync_sheets.sync_reporting_rules import accumulate_write_result, pull_stats_tuple
from app.application.use_cases.sync_sheets.helpers import sync_local_cuadrantes_from_personas
from app.application.use_cases.sync_sheets import payloads_puros
from app.domain.sheets_errors import SheetsConfigError
from app.application.use_cases import sync_sheets_core
from app.application.use_cases.sync_sheets.normalization_rules import normalize_remote_solicitud_row
from app.application.use_cases.sync_sheets.orquestacion_modelos import PullApplyContext
from app.domain.sync_models import SyncSummary
import logging

logger = logging.getLogger(__name__)


class OrquestadorPullSheets:
        _pull_apply_context: PullApplyContext | None

        def __getattr__(self, name: str) -> Any:
            raise AttributeError(name)

        def _pull_with_spreadsheet(self, spreadsheet: Any) -> SyncSummary:
            self._reset_write_batch_state()
            write_calls_before = self._client.get_write_calls_count() if hasattr(self._client, "get_write_calls_count") else 0
            last_sync_at = self._get_last_sync_at()
            downloaded = 0
            conflicts = 0
            omitted_duplicates = 0
            omitted_by_delegada = 0
            errors = 0
            solicitud_titles = self._solicitudes_pull_source_titles(spreadsheet)
            downloaded_count, conflict_count = self._pull_delegadas(spreadsheet, last_sync_at)
            downloaded += downloaded_count
            conflicts += conflict_count
            downloaded_count, conflict_count, duplicate_count, omitted_delegada_count, solicitud_errors = self._pull_solicitudes(
                spreadsheet, last_sync_at, solicitud_titles
            )
            downloaded += downloaded_count
            conflicts += conflict_count
            omitted_duplicates += duplicate_count
            omitted_by_delegada += omitted_delegada_count
            errors += solicitud_errors
            downloaded_count, conflict_count = self._pull_cuadrantes(spreadsheet, last_sync_at)
            downloaded += downloaded_count
            conflicts += conflict_count
            downloaded += self._pull_pdf_log(spreadsheet)
            downloaded += self._pull_config(spreadsheet)
            write_calls_after = self._client.get_write_calls_count() if hasattr(self._client, "get_write_calls_count") else 0
            logger.info("Write calls por sync (pull): %s", write_calls_after - write_calls_before)
            return SyncSummary(
                inserted_local=downloaded,
                updated_local=0,
                duplicates_skipped=omitted_duplicates,
                conflicts_detected=conflicts,
                omitted_by_delegada=omitted_by_delegada,
                errors=errors,
            )

        def _pull_delegadas(self, spreadsheet: Any, last_sync_at: str | None) -> tuple[int, int]:
            worksheet = self._get_worksheet(spreadsheet, "delegadas")
            headers, rows = self._rows_with_index(worksheet, "delegadas")
            downloaded = 0
            conflicts = 0
            for row_number, row in rows:
                row_downloaded, row_conflicts = self._process_pull_delegada_row(
                    worksheet,
                    headers,
                    row_number,
                    row,
                    last_sync_at,
                )
                downloaded += row_downloaded
                conflicts += row_conflicts
            self._flush_write_batches(spreadsheet, worksheet)
            return downloaded, conflicts

        def _process_pull_delegada_row(
            self,
            worksheet: Any,
            headers: list[str],
            row_number: int,
            row: dict[str, Any],
            last_sync_at: str | None,
        ) -> tuple[int, int]:
            uuid_value = payloads_puros.valor_normalizado(row.get("uuid"))
            if payloads_puros.es_fila_vacia(row, ("uuid", "nombre")):
                logger.warning("Fila delegada sin uuid ni nombre; se omite: %s", row)
                return 0, 0
            local_row, was_inserted, persona_uuid = self._get_or_create_persona(row)
            if payloads_puros.requiere_backfill_uuid(self._enable_backfill, row.get("uuid"), persona_uuid):
                self._backfill_uuid(worksheet, headers, row_number, "uuid", str(persona_uuid))
            if was_inserted or not uuid_value or local_row is None or local_row["uuid"] != uuid_value:
                return (1, 0) if was_inserted else (0, 0)
            remote_updated_at = sync_sheets_core.parse_iso(row.get("updated_at"))
            if sync_sheets_core.is_conflict(local_row["updated_at"], remote_updated_at, last_sync_at):
                self._store_conflict("delegadas", uuid_value, dict(local_row), row)
                return 0, 1
            if sync_sheets_core.is_remote_newer(local_row["updated_at"], remote_updated_at):
                self._update_persona_from_remote(local_row["id"], row)
                return 1, 0
            return 0, 0

        def _pull_solicitudes(
            self, spreadsheet: Any, last_sync_at: str | None, solicitud_titles: list[str] | None = None
        ) -> tuple[int, int, int, int, int]:
            stats = {"downloaded": 0, "conflicts": 0, "omitted_duplicates": 0, "omitted_by_delegada": 0, "errors": 0}
            for worksheet_name, worksheet in self._solicitudes_pull_sources(spreadsheet, solicitud_titles):
                worksheet_stats = self._pull_solicitudes_worksheet(worksheet_name, worksheet, last_sync_at)
                for key in stats:
                    stats[key] += worksheet_stats[key]
                logger.info(
                    "Pull solicitudes: worksheet=%s insertadas_local=%s actualizadas_local=%s",
                    worksheet_name,
                    worksheet_stats["inserted_ws"],
                    worksheet_stats["updated_ws"],
                )
                logger.debug(
                    "Pull solicitudes fechas: worksheet=%s ejemplo_antes='%s' ejemplo_despues='%s'",
                    worksheet_name,
                    worksheet_stats["sample_fecha_before"] or "",
                    worksheet_stats["sample_fecha_after"] or "",
                )
                self._flush_write_batches(spreadsheet, worksheet)
            logger.info(
                "Pull solicitudes resumen: insertadas_local=%s omitidas_por_delegada=%s errores=%s",
                stats["downloaded"],
                stats["omitted_by_delegada"],
                stats["errors"],
            )
            return pull_stats_tuple(stats)

        def _pull_solicitudes_worksheet(
            self, worksheet_name: str, worksheet: Any, last_sync_at: str | None
        ) -> dict[str, Any]:
            headers, rows = self._rows_with_index(
                worksheet,
                worksheet_name,
                aliases=self._solicitudes_header_aliases(),
            )
            stats: dict[str, Any] = {
                "downloaded": 0,
                "conflicts": 0,
                "omitted_duplicates": 0,
                "omitted_by_delegada": 0,
                "errors": 0,
                "inserted_ws": 0,
                "updated_ws": 0,
                "sample_fecha_before": None,
                "sample_fecha_after": None,
            }
            logger.info("Pull solicitudes: worksheet=%s filas_leidas=%s", worksheet_name, len(rows))
            self._defer_local_commits = True
            try:
                def _run_rows() -> None:
                    for row_number, raw_row in rows:
                        self._set_pull_solicitud_samples(stats, raw_row)
                        row = normalize_remote_solicitud_row(raw_row, worksheet_name)
                        if stats["sample_fecha_after"] is None:
                            stats["sample_fecha_after"] = str(row.get("fecha") or "")
                        self._process_pull_solicitud_row(worksheet, headers, row_number, row, last_sync_at, stats)

                import app.application.use_cases.sync_sheets.use_case as uc
                uc.run_with_savepoint(self._connection, "pull_solicitudes_worksheet", _run_rows)
            finally:
                self._defer_local_commits = False
            return stats

        @staticmethod
        def _set_pull_solicitud_samples(stats: dict[str, Any], raw_row: dict[str, Any]) -> None:
            if stats["sample_fecha_before"] is None:
                stats["sample_fecha_before"] = str(raw_row.get("fecha") or raw_row.get("fecha_pedida") or "")

        def _process_pull_solicitud_row(self, worksheet: Any, headers: list[str], row_number: int, row: dict[str, Any], last_sync_at: str | None, stats: dict[str, Any]) -> None:
            dto = self.parse_remote_solicitud_row(row)
            context = self.build_pull_context(dto)
            signals = self.build_pull_signals(dto, context.local_row, last_sync_at, stats)
            plan = self._build_pull_solicitud_plan(dto, signals)
            self._apply_pull_solicitud_plan(plan, worksheet, headers, row_number, dto.row, dto.uuid_value, context.local_row, stats)

        @staticmethod
        def _build_pull_solicitud_plan(dto: RemoteSolicitudRowDTO, signals: PullSignals) -> tuple[PullAction, ...]:
            import app.application.use_cases.sync_sheets.use_case as uc
            return uc.plan_pull_actions(
                uc.PullPlannerSignals(
                    has_uuid=bool(dto.uuid_value),
                    has_existing_for_empty_uuid=signals.has_existing_for_empty_uuid,
                    has_local_uuid=signals.has_local_uuid,
                    skip_duplicate=signals.skip_duplicate,
                    conflict_detected=signals.conflict_detected,
                    remote_is_newer=signals.remote_is_newer,
                    backfill_enabled=signals.backfill_enabled,
                    existing_uuid=signals.existing_uuid,
                )
            )


        @staticmethod
        def parse_remote_solicitud_row(row: dict[str, Any]) -> RemoteSolicitudRowDTO:
            import app.application.use_cases.sync_sheets.use_case as uc
            return uc.parse_remote_solicitud_row(
                row,
                normalize_remote_uuid=uc.normalize_remote_uuid,
                parse_iso=uc.sync_sheets_core.parse_iso,
            )

        def build_pull_signals(
            self,
            dto: RemoteSolicitudRowDTO,
            local_row: Any | None,
            last_sync_at: str | None,
            stats: dict[str, Any],
        ) -> PullSignals:
            existing = self._find_solicitud_by_composite_key(dto.row) if not dto.uuid_value else None
            skip_duplicate = bool(dto.uuid_value and local_row is None and self._skip_pull_duplicate(dto.uuid_value, dto.row, stats))
            import app.application.use_cases.sync_sheets.use_case as uc
            return uc.build_pull_signals_snapshot(
                dto=dto,
                local_row=local_row,
                existing=existing,
                skip_duplicate=skip_duplicate,
                enable_backfill=self._enable_backfill,
                is_conflict=sync_sheets_core.is_conflict,
                is_remote_newer=sync_sheets_core.is_remote_newer,
                last_sync_at=last_sync_at,
            )

        def build_pull_context(self, dto: RemoteSolicitudRowDTO) -> PullContext:
            local_row = self._fetch_solicitud(dto.uuid_value) if dto.uuid_value else None
            return PullContext(dto=dto, local_row=local_row)

        def _apply_pull_solicitud_plan(
            self,
            plan: tuple[PullAction, ...],
            worksheet: Any,
            headers: list[str],
            row_number: int,
            row: dict[str, Any],
            uuid_value: str,
            local_row: Any | None,
            stats: dict[str, Any],
        ) -> None:
            self._pull_apply_context = PullApplyContext(worksheet, headers, row_number, row, uuid_value, local_row, stats)
            try:
                import app.application.use_cases.sync_sheets.use_case as uc
                uc.run_pull_actions(
                    plan,
                    on_skip=self._apply_skip_action,
                    on_backfill_uuid=self._apply_backfill_action,
                    on_insert_solicitud=self._apply_insert_solicitud_action,
                    on_update_solicitud=self._apply_update_solicitud_action,
                    on_register_conflict=self._apply_register_conflict_action,
                )
            finally:
                self._pull_apply_context = None

        def _apply_skip_action(self, action: PullAction) -> None:
            context = self._pull_apply_context
            counter = str(action.payload.get("counter") or "")
            import app.application.use_cases.sync_sheets.use_case as uc
            logger.debug("Pull action SKIP: reason_code=%s detail=%s", action.reason_code, uc.reason_text(action.reason_code))
            if context and counter:
                context.stats.update(uc.apply_stat_counter(context.stats, counter=counter))

        def _apply_backfill_action(self, action: PullAction) -> None:
            context = self._pull_apply_context
            target_uuid = str(action.payload.get("uuid") or "")
            if context and target_uuid:
                self._backfill_uuid(context.worksheet, context.headers, context.row_number, "uuid", target_uuid)

        def _apply_insert_solicitud_action(self, action: PullAction) -> None:
            context = self._pull_apply_context
            if not context:
                return
            uuid_payload = action.payload.get("uuid")
            target_uuid = context.uuid_value if uuid_payload == "from_row" else str(uuid_payload or self._generate_uuid())
            context.stats.update(self._accumulate_write_result(context.stats, self._insert_solicitud_from_remote(target_uuid, context.row), "inserted_ws"))
            if not context.uuid_value:
                self._backfill_uuid(context.worksheet, context.headers, context.row_number, "uuid", target_uuid)

        def _apply_update_solicitud_action(self, _: PullAction) -> None:
            context = self._pull_apply_context
            if context and context.local_row is not None:
                context.stats.update(self._accumulate_write_result(context.stats, self._update_solicitud_from_remote(context.local_row["id"], context.row), "updated_ws"))

        def _apply_register_conflict_action(self, _: PullAction) -> None:
            context = self._pull_apply_context
            if context and context.local_row is not None:
                self._store_conflict("solicitudes", context.uuid_value, dict(context.local_row), context.row)
                context.stats["conflicts"] += 1

        def _skip_pull_duplicate(self, uuid_value: str, row: dict[str, Any], stats: dict[str, Any]) -> bool:
            duplicate_key = sync_sheets_core.solicitud_dedupe_key_from_remote_row(row)
            if not duplicate_key or not self._is_duplicate_local_solicitud(duplicate_key, exclude_uuid=uuid_value):
                return False
            logger.info(
                "Omitiendo solicitud duplicada en pull. clave=%s registro=%s",
                duplicate_key,
                row,
            )
            stats["omitted_duplicates"] += 1
            return True

        @staticmethod
        def _accumulate_write_result(stats: dict[str, Any], result: tuple[bool, int, int], operation_counter: str) -> dict[str, Any]:
            return accumulate_write_result(stats, result, operation_counter)

        @staticmethod
        def _solicitudes_header_aliases() -> dict[str, list[str]]:
            return {
                "uuid": ["id", "solicitud_uuid"],
                "delegada_uuid": ["delegado_uuid", "persona_uuid"],
                "delegada_nombre": ["Delegada", "delegado_nombre", "delegada", "delegado", "persona_nombre", "nombre"],
                "fecha": ["fecha_pedida", "dia", "fecha solicitud"],
                "desde": ["desde_hora", "hora_desde"],
                "hasta": ["hasta_hora", "hora_hasta"],
                "completo": ["es_completo", "jornada_completa"],
                "horas": ["minutos_total", "horas_solicitadas", "total_minutos"],
                "notas": ["observaciones", "comentarios"],
            }

        def _solicitudes_pull_source_titles(self, spreadsheet: Any) -> list[str]:
            worksheets_by_title = self._client.get_worksheets_by_title()
            self._worksheet_cache.update(worksheets_by_title)
            titles: list[str] = []
            for name in ("solicitudes", "Histórico", "Historico"):
                if name in worksheets_by_title and name not in titles:
                    titles.append(name)
            if not titles:
                raise SheetsConfigError("No existe worksheet 'solicitudes' ni 'Histórico' en el Spreadsheet.")
            return titles

        def _solicitudes_pull_sources(
            self, spreadsheet: Any, titles: list[str] | None = None
        ) -> list[tuple[str, Any]]:
            selected_titles = titles or self._solicitudes_pull_source_titles(spreadsheet)
            return [(title, self._get_worksheet(spreadsheet, title)) for title in selected_titles]

        def _pull_cuadrantes(
            self, spreadsheet: Any, last_sync_at: str | None
        ) -> tuple[int, int]:
            worksheet = self._get_worksheet(spreadsheet, "cuadrantes")
            _, rows = self._rows_with_index(worksheet)
            downloaded = 0
            conflicts = 0
            for _, row in rows:
                uuid_value = str(row.get("uuid", "")).strip()
                if not uuid_value:
                    continue
                remote_updated_at = sync_sheets_core.parse_iso(row.get("updated_at"))
                local_row = self._fetch_cuadrante(uuid_value)
                if local_row is None:
                    self._insert_cuadrante_from_remote(uuid_value, row)
                    downloaded += 1
                    continue
                if sync_sheets_core.is_conflict(local_row["updated_at"], remote_updated_at, last_sync_at):
                    self._store_conflict("cuadrantes", uuid_value, dict(local_row), row)
                    conflicts += 1
                    continue
                if sync_sheets_core.is_remote_newer(local_row["updated_at"], remote_updated_at):
                    self._update_cuadrante_from_remote(local_row["id"], row)
                    downloaded += 1
            return downloaded, conflicts

        def _pull_pdf_log(self, spreadsheet: Any) -> int:
            worksheet = self._get_worksheet(spreadsheet, "pdf_log")
            _, rows = self._rows_with_index(worksheet)
            cursor = self._connection.cursor()
            downloaded = 0
            for _, row in rows:
                downloaded += self._sync_pdf_log_row(cursor, row)
            if not self._defer_local_commits:
                self._connection.commit()
            return downloaded

        def _sync_pdf_log_row(self, cursor: Any, row: dict[str, Any]) -> int:
            payload = build_pdf_log_payload(row)
            if payload is None:
                return 0
            existing = self._fetch_pdf_log_updated_at(cursor, payload["pdf_id"])
            if existing is None:
                cursor.execute(
                    """
                    INSERT INTO pdf_log (pdf_id, delegada_uuid, rango_fechas, fecha_generacion, hash, updated_at, source_device)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    pdf_log_insert_values(payload),
                )
                return 1
            if self._pdf_log_should_update(existing["updated_at"], payload["updated_at"]):
                cursor.execute(
                    """
                    UPDATE pdf_log
                    SET delegada_uuid = ?, rango_fechas = ?, fecha_generacion = ?, hash = ?, updated_at = ?, source_device = ?
                    WHERE pdf_id = ?
                    """,
                    pdf_log_update_values(payload),
                )
                return 1
            return 0

        @staticmethod
        def _fetch_pdf_log_updated_at(cursor: Any, pdf_id: str) -> Any | None:
            cursor.execute("SELECT updated_at FROM pdf_log WHERE pdf_id = ?", (pdf_id,))
            return cursor.fetchone()

        @staticmethod
        def _pdf_log_should_update(local_updated_at: str | None, remote_updated_at_raw: Any) -> bool:
            remote_updated_at = sync_sheets_core.parse_iso(remote_updated_at_raw)
            return sync_sheets_core.is_remote_newer(local_updated_at, remote_updated_at)

        def _pull_config(self, spreadsheet: Any) -> int:
            worksheet = self._get_worksheet(spreadsheet, "config")
            _, rows = self._rows_with_index(worksheet)
            downloaded = 0
            cursor = self._connection.cursor()
            for _, row in rows:
                key = str(row.get("key", "")).strip()
                if not key:
                    continue
                cursor.execute("SELECT updated_at FROM sync_config WHERE key = ?", (key,))
                existing = cursor.fetchone()
                if existing is None:
                    cursor.execute(
                        """
                        INSERT INTO sync_config (key, value, updated_at, source_device)
                        VALUES (?, ?, ?, ?)
                        """,
                        (key, row.get("value"), row.get("updated_at"), row.get("source_device")),
                    )
                    downloaded += 1
                    self._apply_config_value(key, row.get("value"))
                elif sync_sheets_core.is_remote_newer(existing["updated_at"], sync_sheets_core.parse_iso(row.get("updated_at"))):
                    cursor.execute(
                        """
                        UPDATE sync_config
                        SET value = ?, updated_at = ?, source_device = ?
                        WHERE key = ?
                        """,
                        (row.get("value"), row.get("updated_at"), row.get("source_device"), key),
                    )
                    downloaded += 1
                    self._apply_config_value(key, row.get("value"))
            self._connection.commit()
            return downloaded

        def _sync_local_cuadrantes_from_personas(self) -> None:
            sync_local_cuadrantes_from_personas(self)
