from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


from app.application.sheets_service import SHEETS_SCHEMA
from app.core.errors import InfraError
from app.application.delegada_resolution import get_or_resolve_delegada_uuid
from app.application.use_cases import sync_sheets_core
from app.application.use_cases.sync_sheets.executor import execute_plan
from app.application.use_cases.sync_sheets.helpers import (
    build_solicitudes_sync_plan,
    calcular_bloque_horario_solicitud,
    construir_payload_actualizacion_solicitud,
    construir_payload_insercion_solicitud,
    extraer_datos_delegada,
    normalizar_fechas_solicitud,
    sync_local_cuadrantes_from_personas,
)
from app.application.use_cases.sync_sheets import payloads_puros
from app.application.use_cases.sync_sheets.pull_planner import PullAction, PullPlannerSignals, plan_pull_actions
from app.application.use_cases.sync_sheets.pull_runner import run_pull_actions, run_with_savepoint
from app.application.use_cases.sync_sheets.push_builder import build_push_solicitudes_payloads
from app.application.use_cases.sync_sheets.push_runner import run_push_values_update
from app.application.use_cases.sync_sheets.normalization_rules import normalize_remote_solicitud_row, normalize_remote_uuid
from app.application.use_cases.sync_sheets.persona_resolution_rules import build_persona_resolution_plan
from app.application.use_cases.sync_sheets.planner import build_plan
from app.application.use_cases.sync_sheets.sync_sheets_helpers import (
    execute_with_validation,
    rowcol_to_a1,
    rows_with_index,
)
from app.application.use_cases.sync_sheets import persistence_ops
from app.domain.ports import (
    SheetsClientPort,
    SheetsConfigStorePort,
    SheetsRepositoryPort,
    SqlConnectionPort,
)
from app.domain.sheets_errors import SheetsConfigError, SheetsRateLimitError
from app.domain.sync_models import SyncExecutionPlan, SyncSummary

logger = logging.getLogger(__name__)


HEADER_CANONICO_SOLICITUDES = ["uuid", "delegada_uuid", "delegada_nombre", "fecha", "desde_h", "desde_m", "hasta_h", "hasta_m", "completo", "minutos_total", "notas", "estado", "created_at", "updated_at", "source_device", "deleted", "pdf_id"]


@dataclass
class _PullApplyContext:
    worksheet: Any
    headers: list[str]
    row_number: int
    row: dict[str, Any]
    uuid_value: str
    local_row: Any | None
    stats: dict[str, Any]


@dataclass(frozen=True)
class RemoteSolicitudRowDTO:
    row: dict[str, Any]
    uuid_value: str
    remote_updated_at: datetime | None


@dataclass(frozen=True)
class PullSignals:
    has_existing_for_empty_uuid: bool
    has_local_uuid: bool
    skip_duplicate: bool
    conflict_detected: bool
    remote_is_newer: bool
    backfill_enabled: bool
    existing_uuid: str | None


@dataclass(frozen=True)
class PullContext:
    dto: RemoteSolicitudRowDTO
    local_row: Any | None


class SheetsSyncService:
    def __init__(
        self,
        connection: SqlConnectionPort,
        config_store: SheetsConfigStorePort,
        client: SheetsClientPort,
        repository: SheetsRepositoryPort,
        *,
        enable_backfill: bool = False,
    ) -> None:
        self._connection = connection
        self._config_store = config_store
        self._client = client
        self._repository = repository
        self._worksheet_cache: dict[str, Any] = {}
        self._pending_append_rows: dict[str, list[list[Any]]] = {}
        self._pending_batch_updates: dict[str, list[dict[str, Any]]] = {}
        self._pending_values_batch_updates: dict[str, list[dict[str, Any]]] = {}
        self._enable_backfill = enable_backfill
        self._defer_local_commits = False
        self._pull_apply_context: _PullApplyContext | None = None

    def pull(self) -> SyncSummary:
        spreadsheet = self._ensure_connection_ready()
        summary = self._pull_with_spreadsheet(spreadsheet)
        self._log_sync_stats("pull")
        return summary

    def push(self) -> SyncSummary:
        spreadsheet = self._ensure_connection_ready()
        summary = self._push_with_spreadsheet(spreadsheet)
        self._log_sync_stats("push")
        return summary

    def sync(self) -> SyncSummary:
        return self.sync_bidirectional()

    def sync_bidirectional(self) -> SyncSummary:
        spreadsheet = self._ensure_connection_ready()
        pull_summary = self._pull_with_spreadsheet(spreadsheet)
        # Garantiza persistencia local del pull antes de cualquier push/refresh de UI.
        self._connection.commit()
        push_summary = self._push_with_spreadsheet(spreadsheet)
        self._log_sync_stats("sync_bidirectional")
        return SyncSummary(
            inserted_local=pull_summary.inserted_local,
            updated_local=pull_summary.updated_local,
            inserted_remote=push_summary.inserted_remote,
            updated_remote=push_summary.updated_remote,
            duplicates_skipped=pull_summary.duplicates_skipped + push_summary.duplicates_skipped,
            conflicts_detected=pull_summary.conflicts_detected + push_summary.conflicts_detected,
            omitted_by_delegada=pull_summary.omitted_by_delegada + push_summary.omitted_by_delegada,
            errors=pull_summary.errors + push_summary.errors,
        )

    def simulate_sync_plan(self) -> SyncExecutionPlan:
        spreadsheet = self._ensure_connection_ready()
        return build_plan(self, spreadsheet)

    def execute_sync_plan(self, plan: SyncExecutionPlan) -> SyncSummary:
        spreadsheet = self._ensure_connection_ready()
        return execute_plan(self, spreadsheet, plan)

    def get_last_sync_at(self) -> str | None:
        return self._get_last_sync_at()

    def is_configured(self) -> bool:
        config = self._config_store.load()
        return bool(config and config.spreadsheet_id and config.credentials_path)

    def ensure_connection(self) -> None:
        self._ensure_connection_ready()

    def store_sync_config_value(self, key: str, value: str) -> None:
        if not self.is_configured():
            return
        cursor = self._connection.cursor()
        now_iso = self._now_iso()
        cursor.execute(
            """
            INSERT INTO sync_config (key, value, updated_at, source_device)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                updated_at = excluded.updated_at,
                source_device = excluded.source_device
            """,
            (key, value, now_iso, self._device_id()),
        )
        self._connection.commit()

    def register_pdf_log(self, persona_id: int, fechas: list[str], pdf_hash: str | None) -> None:
        if not pdf_hash:
            return
        cursor = self._connection.cursor()
        cursor.execute("SELECT uuid FROM personas WHERE id = ?", (persona_id,))
        row = cursor.fetchone()
        if not row:
            return
        delegada_uuid = row["uuid"]
        rango = self._format_rango_fechas(fechas)
        now_iso = self._now_iso()
        cursor.execute(
            """
            INSERT INTO pdf_log (pdf_id, delegada_uuid, rango_fechas, fecha_generacion, hash, updated_at, source_device)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(pdf_id) DO UPDATE SET
                delegada_uuid = excluded.delegada_uuid,
                rango_fechas = excluded.rango_fechas,
                fecha_generacion = excluded.fecha_generacion,
                hash = excluded.hash,
                updated_at = excluded.updated_at,
                source_device = excluded.source_device
            """,
            (
                pdf_hash,
                delegada_uuid,
                rango,
                now_iso,
                pdf_hash,
                now_iso,
                self._device_id(),
            ),
        )
        self._connection.commit()

    def _prepare_sync_context(self, spreadsheet: Any) -> None:
        self._worksheet_cache = {}
        try:
            self._worksheet_cache.update(self._client.get_worksheets_by_title())
        except SheetsRateLimitError:
            raise
        except InfraError:
            logger.debug("No se pudo precargar metadata de worksheets; se continuará bajo demanda.", exc_info=True)

    def _get_worksheet(self, spreadsheet: Any, worksheet_name: str) -> Any:
        if worksheet_name in self._worksheet_cache:
            return self._worksheet_cache[worksheet_name]
        worksheet = self._client.get_worksheet(worksheet_name)
        self._worksheet_cache[worksheet_name] = worksheet
        return worksheet

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

    def _ensure_connection_ready(self) -> Any:
        spreadsheet = self._open_spreadsheet()
        self._prepare_sync_context(spreadsheet)
        self._repository.ensure_schema(spreadsheet, SHEETS_SCHEMA)
        return spreadsheet

    def _open_spreadsheet(self) -> Any:
        config = self._config_store.load()
        if not config or not config.spreadsheet_id or not config.credentials_path:
            raise SheetsConfigError("No hay configuración de Google Sheets.")
        credentials_path = Path(config.credentials_path)
        spreadsheet = self._client.open_spreadsheet(credentials_path, config.spreadsheet_id)
        return spreadsheet

    def _get_last_sync_at(self) -> str | None:
        cursor = self._connection.cursor()
        try:
            cursor.execute("SELECT last_sync_at FROM sync_state WHERE id = 1")
        except Exception as exc:
            # CI y pruebas aisladas pueden inicializar una conexión sin migraciones.
            # Devolvemos None para mantener la app operativa sin romper el arranque.
            if "no such table: sync_state" in str(exc).lower():
                logger.warning("sync_state table missing; returning empty last_sync_at")
                return None
            raise
        row = cursor.fetchone()
        if not row:
            return None
        return row["last_sync_at"]

    def _set_last_sync_at(self, timestamp: str) -> None:
        cursor = self._connection.cursor()
        cursor.execute(
            "UPDATE sync_state SET last_sync_at = ? WHERE id = 1",
            (timestamp,),
        )
        self._connection.commit()

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
        return (
            stats["downloaded"],
            stats["conflicts"],
            stats["omitted_duplicates"],
            stats["omitted_by_delegada"],
            stats["errors"],
        )

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

            run_with_savepoint(self._connection, "pull_solicitudes_worksheet", _run_rows)
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
        return plan_pull_actions(
            PullPlannerSignals(
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
        uuid_value = normalize_remote_uuid(row.get("uuid"))
        remote_updated_at = sync_sheets_core.parse_iso(row.get("updated_at")) if uuid_value else None
        return RemoteSolicitudRowDTO(row=row, uuid_value=uuid_value, remote_updated_at=remote_updated_at)

    def build_pull_signals(
        self,
        dto: RemoteSolicitudRowDTO,
        local_row: Any | None,
        last_sync_at: str | None,
        stats: dict[str, Any],
    ) -> PullSignals:
        existing = self._find_solicitud_by_composite_key(dto.row) if not dto.uuid_value else None
        existing_uuid = str(existing["uuid"] or "").strip() if existing is not None else None
        skip_duplicate = bool(dto.uuid_value and local_row is None and self._skip_pull_duplicate(dto.uuid_value, dto.row, stats))
        return PullSignals(
            has_existing_for_empty_uuid=existing is not None,
            has_local_uuid=local_row is not None,
            skip_duplicate=skip_duplicate,
            conflict_detected=bool(local_row and sync_sheets_core.is_conflict(local_row["updated_at"], dto.remote_updated_at, last_sync_at)),
            remote_is_newer=bool(local_row and sync_sheets_core.is_remote_newer(local_row["updated_at"], dto.remote_updated_at)),
            backfill_enabled=self._enable_backfill,
            existing_uuid=existing_uuid,
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
        self._pull_apply_context = _PullApplyContext(worksheet, headers, row_number, row, uuid_value, local_row, stats)
        try:
            run_pull_actions(
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
        if context and counter:
            context.stats[counter] = context.stats.get(counter, 0) + 1

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
        self._accumulate_write_result(context.stats, self._insert_solicitud_from_remote(target_uuid, context.row), "inserted_ws")
        if not context.uuid_value:
            self._backfill_uuid(context.worksheet, context.headers, context.row_number, "uuid", target_uuid)

    def _apply_update_solicitud_action(self, _: PullAction) -> None:
        context = self._pull_apply_context
        if context and context.local_row is not None:
            self._accumulate_write_result(context.stats, self._update_solicitud_from_remote(context.local_row["id"], context.row), "updated_ws")

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
    def _accumulate_write_result(stats: dict[str, Any], result: tuple[bool, int, int], operation_counter: str) -> None:
        written, omitted_delegada, operation_errors = result
        stats["downloaded"] += 1 if written else 0
        stats[operation_counter] += 1 if written else 0
        stats["omitted_by_delegada"] += omitted_delegada
        stats["errors"] += operation_errors

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
        payload = self._build_pdf_log_payload(row)
        if payload is None:
            return 0
        existing = self._fetch_pdf_log_updated_at(cursor, payload["pdf_id"])
        if existing is None:
            cursor.execute(
                """
                INSERT INTO pdf_log (pdf_id, delegada_uuid, rango_fechas, fecha_generacion, hash, updated_at, source_device)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                self._pdf_log_insert_values(payload),
            )
            return 1
        if self._pdf_log_should_update(existing["updated_at"], payload["updated_at"]):
            cursor.execute(
                """
                UPDATE pdf_log
                SET delegada_uuid = ?, rango_fechas = ?, fecha_generacion = ?, hash = ?, updated_at = ?, source_device = ?
                WHERE pdf_id = ?
                """,
                self._pdf_log_update_values(payload),
            )
            return 1
        return 0

    @staticmethod
    def _build_pdf_log_payload(row: dict[str, Any]) -> dict[str, Any] | None:
        pdf_id = str(row.get("pdf_id", "")).strip()
        if not pdf_id:
            return None
        return {
            "pdf_id": pdf_id,
            "delegada_uuid": row.get("delegada_uuid"),
            "rango_fechas": row.get("rango_fechas"),
            "fecha_generacion": row.get("fecha_generacion"),
            "hash": row.get("hash"),
            "updated_at": row.get("updated_at"),
            "source_device": row.get("source_device"),
        }

    @staticmethod
    def _fetch_pdf_log_updated_at(cursor: Any, pdf_id: str) -> Any | None:
        cursor.execute("SELECT updated_at FROM pdf_log WHERE pdf_id = ?", (pdf_id,))
        return cursor.fetchone()

    @staticmethod
    def _pdf_log_should_update(local_updated_at: str | None, remote_updated_at_raw: Any) -> bool:
        remote_updated_at = sync_sheets_core.parse_iso(remote_updated_at_raw)
        return sync_sheets_core.is_remote_newer(local_updated_at, remote_updated_at)

    @staticmethod
    def _pdf_log_insert_values(payload: dict[str, Any]) -> tuple[Any, ...]:
        return (
            payload["pdf_id"],
            payload["delegada_uuid"],
            payload["rango_fechas"],
            payload["fecha_generacion"],
            payload["hash"],
            payload["updated_at"],
            payload["source_device"],
        )

    @staticmethod
    def _pdf_log_update_values(payload: dict[str, Any]) -> tuple[Any, ...]:
        return (
            payload["delegada_uuid"],
            payload["rango_fechas"],
            payload["fecha_generacion"],
            payload["hash"],
            payload["updated_at"],
            payload["source_device"],
            payload["pdf_id"],
        )

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

    def _push_pdf_log(self, spreadsheet: Any, last_sync_at: str | None) -> int:
        worksheet = self._get_worksheet(spreadsheet, "pdf_log")
        headers, rows = self._rows_with_index(worksheet)
        header_map = self._header_map(headers, SHEETS_SCHEMA["pdf_log"])
        remote_index = {row["pdf_id"]: row for _, row in rows if row.get("pdf_id")}
        cursor = self._connection.cursor()
        cursor.execute(
            """
            SELECT pdf_id, delegada_uuid, rango_fechas, fecha_generacion, hash, updated_at, source_device
            FROM pdf_log
            WHERE updated_at IS NOT NULL
            """
        )
        uploaded = 0
        for row in cursor.fetchall():
            if not sync_sheets_core.is_after_last_sync(row["updated_at"], last_sync_at):
                continue
            remote_row = remote_index.get(row["pdf_id"])
            remote_updated_at = sync_sheets_core.parse_iso(remote_row.get("updated_at") if remote_row else None)
            local_updated_at = sync_sheets_core.parse_iso(row["updated_at"])
            if remote_row and remote_updated_at and local_updated_at and remote_updated_at > local_updated_at:
                continue
            payload = {
                "pdf_id": row["pdf_id"],
                "delegada_uuid": row["delegada_uuid"],
                "rango_fechas": row["rango_fechas"],
                "fecha_generacion": row["fecha_generacion"],
                "hash": row["hash"],
                "updated_at": row["updated_at"],
                "source_device": row["source_device"] or self._device_id(),
            }
            if remote_row:
                if self._enable_backfill:
                    row_number = remote_row["__row_number__"]
                    self._update_row(worksheet, row_number, header_map, payload)
                continue
            self._append_row(worksheet, header_map, payload)
            uploaded += 1
        self._flush_write_batches(spreadsheet, worksheet)
        return uploaded

    def _push_config(self, spreadsheet: Any, last_sync_at: str | None) -> int:
        worksheet = self._get_worksheet(spreadsheet, "config")
        headers, rows = self._rows_with_index(worksheet)
        header_map = self._header_map(headers, SHEETS_SCHEMA["config"])
        remote_index = {row["key"]: row for _, row in rows if row.get("key")}
        cursor = self._connection.cursor()
        cursor.execute(
            """
            SELECT key, value, updated_at, source_device
            FROM sync_config
            WHERE updated_at IS NOT NULL
            """
        )
        uploaded = 0
        for row in cursor.fetchall():
            if not sync_sheets_core.is_after_last_sync(row["updated_at"], last_sync_at):
                continue
            remote_row = remote_index.get(row["key"])
            remote_updated_at = sync_sheets_core.parse_iso(remote_row.get("updated_at") if remote_row else None)
            local_updated_at = sync_sheets_core.parse_iso(row["updated_at"])
            if remote_row and remote_updated_at and local_updated_at and remote_updated_at > local_updated_at:
                continue
            payload = {
                "key": row["key"],
                "value": row["value"],
                "updated_at": row["updated_at"],
                "source_device": row["source_device"] or self._device_id(),
            }
            if remote_row:
                if self._enable_backfill:
                    row_number = remote_row["__row_number__"]
                    self._update_row(worksheet, row_number, header_map, payload)
                continue
            self._append_row(worksheet, header_map, payload)
            uploaded += 1
        self._flush_write_batches(spreadsheet, worksheet)
        return uploaded

    def _push_delegadas(
        self, spreadsheet: Any, last_sync_at: str | None
    ) -> tuple[int, int]:
        worksheet = self._get_worksheet(spreadsheet, "delegadas")
        headers, rows = self._rows_with_index(worksheet)
        header_map = self._header_map(headers, SHEETS_SCHEMA["delegadas"])
        remote_index = self._uuid_index(rows)
        cursor = self._connection.cursor()
        cursor.execute(
            """
            SELECT id, uuid, nombre, genero, is_active, horas_mes_min, horas_ano_min,
                   updated_at, source_device, deleted
            FROM personas
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
                self._store_conflict("delegadas", uuid_value, dict(row), remote_row or {})
                conflicts += 1
                continue
            payload = {
                "uuid": uuid_value,
                "nombre": row["nombre"],
                "genero": row["genero"],
                "activa": 1 if row["is_active"] else 0,
                "bolsa_mes_min": row["horas_mes_min"] or 0,
                "bolsa_anual_min": row["horas_ano_min"] or 0,
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

    def _push_solicitudes(
        self, spreadsheet: Any, last_sync_at: str | None
    ) -> tuple[int, int, int]:
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
        result = build_push_solicitudes_payloads(
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

        run_push_values_update(worksheet, result.values, retries=2)
        logger.info("PUSH Sheets: %s filas enviadas", max(len(result.values) - 1, 0))
        return result.uploaded, len(result.conflicts), result.omitted_duplicates

    def _build_solicitudes_sync_plan(self, spreadsheet: Any) -> SyncExecutionPlan:
        return build_solicitudes_sync_plan(self, spreadsheet, HEADER_CANONICO_SOLICITUDES)

    def _local_solicitud_payload(self, row: Any) -> tuple[Any, ...]:
        return (
            row["uuid"],
            row["delegada_uuid"] or "",
            row["delegada_nombre"] or "",
            sync_sheets_core.to_iso_date(row["fecha_pedida"]),
            sync_sheets_core.split_minutes(row["desde_min"])[0],
            sync_sheets_core.split_minutes(row["desde_min"])[1],
            sync_sheets_core.split_minutes(row["hasta_min"])[0],
            sync_sheets_core.split_minutes(row["hasta_min"])[1],
            1 if row["completo"] else 0,
            sync_sheets_core.int_or_zero(row["horas_solicitadas_min"]),
            row["notas"] or "",
            "",
            sync_sheets_core.to_iso_date(row["created_at"]),
            sync_sheets_core.to_iso_date(row["updated_at"]),
            row["source_device"] or self._device_id(),
            sync_sheets_core.int_or_zero(row["deleted"]),
            row["pdf_hash"] or "",
        )

    def _remote_solicitud_payload(self, remote_row: dict[str, Any]) -> tuple[Any, ...]:
        return payloads_puros.payload_remoto_solicitud(remote_row)

    def _push_cuadrantes(
        self, spreadsheet: Any, last_sync_at: str | None
    ) -> tuple[int, int]:
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
        resolved_uuid = get_or_resolve_delegada_uuid(self._connection, delegada_uuid, delegada_nombre)
        if not resolved_uuid:
            logger.warning("Solicitud omitida por delegada no resuelta: %s", identificador)
            return None
        persona_id = self._persona_id_from_uuid(resolved_uuid)
        if persona_id is None:
            logger.warning("Solicitud omitida por delegada no resuelta: %s", identificador)
            return None
        logger.info("Delegada resuelta: %s %s", resolved_uuid, delegada_nombre)
        return persona_id

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
        dia = self._normalize_dia(str(row.get("dia_semana", "")))
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

    def _sync_local_cuadrantes_from_personas(self) -> None:
        sync_local_cuadrantes_from_personas(self)

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
        # Evita write-per-row: acumulamos updates y se ejecutan en un único batch_update por worksheet.
        row_values = [payload.get(header, "") for header in headers]
        range_name = f"A{row_number}:{rowcol_to_a1(row_number, len(headers))}"
        self._pending_batch_updates.setdefault(worksheet.title, []).append({"range": range_name, "values": [row_values]})

    def _append_row(self, worksheet: Any, headers: list[str], payload: dict[str, Any]) -> None:
        # Evita write-per-row: acumulamos altas y se ejecutan en un único append_rows por worksheet.
        row_values = [payload.get(header, "") for header in headers]
        self._pending_append_rows.setdefault(worksheet.title, []).append(row_values)


    def _reset_write_batch_state(self) -> None:
        self._pending_append_rows = {}
        self._pending_batch_updates = {}
        self._pending_values_batch_updates = {}

    def _queue_values_batch_update(self, worksheet: Any, row_number: int, col_idx: int, value: Any) -> None:
        a1_cell = rowcol_to_a1(row_number, col_idx)
        sheet_title = worksheet.title.replace("'", "''")
        range_name = f"'{sheet_title}'!{a1_cell}"
        self._pending_values_batch_updates.setdefault(worksheet.title, []).append({"range": range_name, "values": [[value]]})

    def _flush_write_batches(self, spreadsheet: Any, worksheet: Any) -> None:
        worksheet_title = worksheet.title
        appended_rows = self._pending_append_rows.pop(worksheet_title, [])
        updated_rows = self._pending_batch_updates.pop(worksheet_title, [])
        backfills = self._pending_values_batch_updates.pop(worksheet_title, [])

        if appended_rows:
            if hasattr(self._client, "append_rows"):
                self._client.append_rows(worksheet_title, appended_rows)
            else:
                worksheet.append_rows(appended_rows, value_input_option="USER_ENTERED")
            logger.info("Write batch (%s): %s rows appended", worksheet_title, len(appended_rows))

        if updated_rows:
            if hasattr(self._client, "batch_update"):
                self._client.batch_update(worksheet_title, updated_rows)
            else:
                worksheet.batch_update(updated_rows, value_input_option="USER_ENTERED")
            logger.info("Write batch (%s): %s rows updated", worksheet_title, len(updated_rows))

        if backfills:
            body = {"valueInputOption": "USER_ENTERED", "data": backfills}
            if hasattr(self._client, "values_batch_update"):
                self._client.values_batch_update(body)
            else:
                spreadsheet.values_batch_update(body)
            logger.info("Write batch: %s rows updated", len(backfills))

    def _log_sync_stats(self, operation: str) -> None:
        read_count = self._client.get_read_calls_count() if hasattr(self._client, "get_read_calls_count") else "n/a"
        write_count = self._client.get_write_calls_count() if hasattr(self._client, "get_write_calls_count") else "n/a"
        avoided = self._client.get_avoided_requests_count() if hasattr(self._client, "get_avoided_requests_count") else "n/a"
        logger.info(
            "Sync stats (%s): read_count=%s write_count=%s avoided_requests=%s",
            operation,
            read_count,
            write_count,
            avoided,
        )

    @staticmethod
    def _normalize_dia(dia: str) -> str | None:
        value = dia.strip().lower()
        mapping = {
            "lunes": "lun",
            "martes": "mar",
            "miercoles": "mie",
            "miércoles": "mie",
            "jueves": "jue",
            "viernes": "vie",
            "sabado": "sab",
            "sábado": "sab",
            "domingo": "dom",
        }
        if value in mapping:
            return mapping[value]
        if value in {"lun", "mar", "mie", "jue", "vie", "sab", "dom"}:
            return value
        return None

    @staticmethod
    def _solicitud_dedupe_key_from_remote_row(row: dict[str, Any]) -> tuple[object, ...] | None:
        return sync_sheets_core.solicitud_dedupe_key_from_remote_row(row)

    @staticmethod
    def _solicitud_dedupe_key_from_local_row(row: dict[str, Any]) -> tuple[object, ...] | None:
        return sync_sheets_core.solicitud_dedupe_key_from_local_row(row)

    def _is_duplicate_local_solicitud(self, key: tuple[object, ...], exclude_uuid: str | None = None) -> bool:
        return persistence_ops.is_duplicate_local_solicitud(self._connection, key, exclude_uuid)

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    def _device_id(self) -> str:
        config = self._config_store.load()
        return config.device_id if config else ""

    def _apply_config_value(self, key: str, value: Any) -> None:
        if key != "pdf_text":
            return
        cursor = self._connection.cursor()
        cursor.execute(
            """
            UPDATE grupo_config
            SET pdf_intro_text = ?
            WHERE id = 1
            """,
            (value or "",),
        )

    @staticmethod
    def _format_rango_fechas(fechas: list[str]) -> str:
        fechas_filtradas = sorted({fecha for fecha in fechas if fecha})
        if not fechas_filtradas:
            return ""
        if len(fechas_filtradas) == 1:
            return fechas_filtradas[0]
        return f"{fechas_filtradas[0]} - {fechas_filtradas[-1]}"

    @staticmethod
    def _generate_uuid() -> str:
        return str(uuid.uuid4())
