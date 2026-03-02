from __future__ import annotations

import logging
from pathlib import Path

try:
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication, QDialog, QHBoxLayout, QPushButton, QTreeWidget, QTreeWidgetItem, QVBoxLayout
except Exception:  # pragma: no cover - habilita import en CI sin Qt
    QApplication = QDialog = QHBoxLayout = QPushButton = QTreeWidget = QTreeWidgetItem = QVBoxLayout = object
    Qt = object

from app.domain.sync_models import SyncSummary
from app.ui import dialogos_comunes
from app.ui.copy_catalog import copy_text
from app.ui.patterns import STATUS_PATTERNS, apply_modal_behavior, status_badge
from app.ui.sync_reporting import list_sync_history, load_sync_report, persist_report, to_markdown
from app.ui.toast_helpers import toast_success


logger = logging.getLogger(__name__)


def _resolve_status_label(ventana, status: str) -> str:
    resolver = getattr(ventana, "_status_to_label", None)
    if callable(resolver):
        return resolver(status)
    return status_to_label(status)


def apply_sync_report(ventana, report) -> None:
    ventana._last_sync_report = report
    ventana._sync_attempts.append({"status": report.status, "counts": report.counts})
    counts = report.counts
    set_sync_status_badge(ventana, report.status)
    ventana.sync_source_label.setText(f"{copy_text('ui.sync.fuente_label')} {report.source}")
    ventana.sync_scope_label.setText(f"{copy_text('ui.sync.rango_label')} {report.scope}")
    ventana.sync_idempotency_label.setText(f"{copy_text('ui.sync.evita_duplicados_label')} {report.idempotency_criteria}")
    ventana.sync_counts_label.setText(
        f"{copy_text('ui.sync.resumen_filas')}: "
        f"{copy_text('ui.sync.filas_creadas_label')} {counts.get('created', 0)} · "
        f"{copy_text('ui.sync.bullet_filas_actualizadas')} {counts.get('updated', 0)} · "
        f"{copy_text('ui.sync.bullet_filas_omitidas')} {counts.get('skipped', 0)} · "
        f"{copy_text('ui.sync.bullet_conflictos')} {counts.get('conflicts', 0)} · "
        f"{copy_text('ui.sync.bullet_errores')} {counts.get('errors', 0)}"
    )
    ventana.sync_panel_status.setText(
        copy_text("ui.sync.estado_intento_actual_final").format(
            intento=len(ventana._sync_attempts),
            actual=_resolve_status_label(ventana, report.status),
            final=_resolve_status_label(ventana, report.final_status),
        )
    )
    ventana.last_sync_metrics_label.setText(
        f"{copy_text('ui.sync.duracion_label')} {report.duration_ms} {copy_text('ui.sync.ms')} · "
        f"{copy_text('ui.sync.cambios_label')} {counts.get('created', 0) + counts.get('updated', 0)} · "
        f"{copy_text('ui.sync.bullet_conflictos')} {report.conflicts_count} · {copy_text('ui.sync.bullet_errores')} {report.error_count}"
    )
    ventana._refresh_sync_trend_label()
    ventana.go_to_sync_config_button.setVisible(report.status == "CONFIG_INCOMPLETE")
    ventana.sync_details_button.setEnabled(True)
    ventana.copy_sync_report_button.setEnabled(True)
    ventana.retry_failed_button.setEnabled(bool(report.errors or report.conflicts))
    ventana.review_conflicts_button.setText(
        copy_text("ui.sync.revisar_conflictos")
        if report.conflicts_count > 0
        else copy_text("ui.sync.revisar_conflictos_sin_pendientes")
    )
    ventana._update_conflicts_reminder()
    persist_report(report, Path.cwd())
    ventana._refresh_health_and_alerts()


def on_show_sync_history(ventana) -> None:
    history = list_sync_history(Path.cwd())
    if not history:
        ventana.toast.info(copy_text("ui.sync.no_hay_historico"), title=copy_text("ui.sync.historico"))
        return
    dialog = QDialog(ventana)
    dialog.setWindowTitle(copy_text("ui.sync.historico_sincronizaciones"))
    dialog.resize(800, 420)
    layout = QVBoxLayout(dialog)
    table = QTreeWidget(dialog)
    table.setColumnCount(4)
    table.setHeaderLabels(
        [
            copy_text("ui.sync.columna_archivo"),
            copy_text("ui.sync.columna_sync_id"),
            copy_text("ui.sync.columna_estado"),
            copy_text("ui.sync.columna_intentos"),
        ]
    )
    for path in history:
        report = load_sync_report(path)
        item = QTreeWidgetItem([path.name, report.sync_id, report.final_status, str(report.attempts)])
        item.setData(0, Qt.UserRole, str(path))
        table.addTopLevelItem(item)
    layout.addWidget(table)

    def _open_selected() -> None:
        selected = table.selectedItems()
        if not selected:
            return
        report_path = Path(selected[0].data(0, Qt.UserRole))
        ventana._last_sync_report = load_sync_report(report_path)
        show_sync_details_dialog(ventana)

    actions = QHBoxLayout()
    open_btn = QPushButton(copy_text("ui.sync.abrir_detalle"))
    open_btn.clicked.connect(_open_selected)
    copy_btn = QPushButton(copy_text("ui.sync.copiar_informe"))
    copy_btn.clicked.connect(
        lambda: QApplication.clipboard().setText(to_markdown(load_sync_report(Path(table.selectedItems()[0].data(0, Qt.UserRole)))))
        if table.selectedItems()
        else None
    )
    actions.addWidget(open_btn)
    actions.addWidget(copy_btn)
    layout.addLayout(actions)
    dialog.exec()


def show_sync_details_dialog(ventana) -> None:
    report = ventana._last_sync_report
    if report is None:
        return
    dialog = QDialog(ventana)
    dialog.setWindowTitle(copy_text("ui.sync.detalles_sincronizacion"))
    dialog.resize(940, 480)
    apply_modal_behavior(dialog)
    layout = QVBoxLayout(dialog)
    table = QTreeWidget(dialog)
    table.setColumnCount(6)
    table.setHeaderLabels(
        [
            copy_text("ui.sync.columna_timestamp"),
            copy_text("ui.sync.columna_sev"),
            copy_text("ui.sync.columna_entidad"),
            copy_text("ui.sync.columna_mensaje"),
            copy_text("ui.sync.columna_accion_sugerida"),
            copy_text("ui.sync.columna_seccion"),
        ]
    )
    for entry in report.entries:
        item = QTreeWidgetItem([entry.timestamp, entry.severity, entry.entity, entry.message, entry.suggested_action, entry.section])
        table.addTopLevelItem(item)
    table.header().setStretchLastSection(True)
    layout.addWidget(table, 1)

    actions = QHBoxLayout()
    open_affected = QPushButton(copy_text("ui.sync.abrir_solicitud_afectada"))
    open_affected.setProperty("variant", "secondary")
    open_affected.setEnabled(bool(report.conflicts))
    open_affected.clicked.connect(ventana._on_review_conflicts)
    actions.addWidget(open_affected)

    mark_review = QPushButton(copy_text("ui.sync.marcar_para_revision"))
    mark_review.setProperty("variant", "secondary")
    mark_review.setEnabled(bool(report.conflicts))
    mark_review.clicked.connect(lambda: ventana.toast.info(copy_text("ui.sync.registro_marcado_revision_manual")))
    actions.addWidget(mark_review)

    retry_failed = QPushButton(copy_text("ui.sync.reintentar_solo_fallidos"))
    retry_failed.setProperty("variant", "secondary")
    retry_failed.setEnabled(bool(report.errors or report.conflicts))
    retry_failed.clicked.connect(ventana._on_retry_failed)
    actions.addWidget(retry_failed)

    export_detail = QPushButton(copy_text("ui.sync.exportar_detalle"))
    export_detail.setProperty("variant", "secondary")
    export_detail.clicked.connect(ventana._on_copy_sync_report)
    actions.addWidget(export_detail)

    close_button = QPushButton(copy_text("ui.comun.cerrar"))
    close_button.setProperty("variant", "ghost")
    close_button.clicked.connect(dialog.accept)
    actions.addWidget(close_button)
    layout.addLayout(actions)
    dialog.exec()


def set_sync_status_badge(ventana, status: str) -> None:
    ventana.sync_status_badge.setText(_resolve_status_label(ventana, status))
    tone_map = {
        "OK": STATUS_PATTERNS["CONFIRMED"].tone,
        "RUNNING": STATUS_PATTERNS["PENDING"].tone,
        "OK_WARN": STATUS_PATTERNS["WARNING"].tone,
        "ERROR": STATUS_PATTERNS["ERROR"].tone,
    }
    ventana.sync_status_badge.setProperty("tone", tone_map.get(status, "pending"))
    ventana.sync_status_badge.setProperty("syncStatus", status)
    style = ventana.sync_status_badge.style()
    if style is not None:
        style.unpolish(ventana.sync_status_badge)
        style.polish(ventana.sync_status_badge)
    ventana.sync_status_badge.update()
    ventana._update_global_context()


def status_from_summary(summary: SyncSummary) -> str:
    if summary.errors > 0:
        return "ERROR"
    if summary.conflicts_detected > 0 or summary.duplicates_skipped > 0 or summary.omitted_by_delegada > 0:
        return "OK_WARN"
    return "OK"


def status_to_label(status: str) -> str:
    return {
        "IDLE": copy_text("ui.sync.estado_en_espera"),
        "RUNNING": copy_text("ui.sync.estado_pendiente_sincronizando"),
        "OK": status_badge("CONFIRMED"),
        "OK_WARN": status_badge("WARNING"),
        "ERROR": status_badge("ERROR"),
        "CONFIG_INCOMPLETE": copy_text("ui.sync.estado_error_config_incompleta"),
    }.get(status, status)


def sync_source_text(ventana) -> str:
    config = ventana._sheets_service.get_config()
    if not config:
        return copy_text("ui.sync.error_configura_credenciales")
    credentials_name = Path(config.credentials_path).name if config.credentials_path else copy_text("ui.sync.sin_archivo")
    sheet_short = f"…{config.spreadsheet_id[-6:]}" if config.spreadsheet_id else "sin-id"
    return (
        f"{copy_text('ui.sync.spreadsheet_label')} {sheet_short} "
        f"{copy_text('ui.sync.bullet_credencial')} {credentials_name}"
    )


def sync_scope_text() -> str:
    return copy_text("ui.sync.sincronizacion_completa")


def sync_actor_text(ventana) -> str:
    persona = ventana._current_persona()
    return persona.nombre if persona is not None else copy_text("ui.sync.delegada_no_seleccionada")


def show_sync_summary_dialog(ventana, title: str, summary: SyncSummary) -> None:
    last_sync = ventana._sync_service.get_last_sync_at()
    last_sync_text = ventana._format_timestamp(last_sync) if last_sync else copy_text("ui.sync.nunca")
    message = (
        f"{copy_text('ui.sync.insertadas_local_label')} {summary.inserted_local}\n"
        f"{copy_text('ui.sync.actualizadas_local_label')} {summary.updated_local}\n"
        f"{copy_text('ui.sync.resumen_insertadas')} {summary.inserted_remote}\n"
        f"{copy_text('ui.sync.resumen_actualizadas')} {summary.updated_remote}\n"
        f"{copy_text('ui.sync.resumen_duplicados_omitidos')} {summary.duplicates_skipped}\n"
        f"{copy_text('ui.sync.resumen_omitidas_delegada')} {summary.omitted_by_delegada}\n"
        f"{copy_text('ui.sync.resumen_conflictos')} {summary.conflicts_detected}\n"
        f"{copy_text('ui.sync.resumen_errores')} {summary.errors}\n"
        f"{copy_text('ui.sync.resumen_ultima_sincronizacion')} {last_sync_text}"
    )
    if summary.conflicts_detected > 0 or summary.errors > 0:
        ventana.toast.warning(message, title=title, duration_ms=7000)
        show_details_dialog(ventana, title, message)
    else:
        toast_success(ventana.toast, message, title=title)


def show_message_with_details(
    ventana,
    title: str,
    message: str,
    details: str | None,
    icon,
    action_buttons: tuple[tuple[str, object], ...] = (),
) -> None:
    dialogos_comunes.show_message_with_details(ventana, title, message, details, icon, action_buttons)


def show_details_dialog(ventana, title: str, details: str) -> None:
    dialogos_comunes.show_details_dialog(ventana, title, details)


def service_account_email(ventana) -> str | None:
    sync_service = getattr(ventana, "_sync_service", None)
    if sync_service is not None and hasattr(sync_service, "get_service_account_email"):
        account_email = sync_service.get_service_account_email()
        if isinstance(account_email, str) and account_email.strip():
            return account_email.strip()
    config = ventana._sheets_service.get_config()
    account_email = getattr(config, "service_account_email", None) if config is not None else None
    if isinstance(account_email, str) and account_email.strip():
        return account_email.strip()
    logger.warning(
        "SHEETS_SERVICE_EMAIL_MISSING",
        extra={"event": "SHEETS_SERVICE_EMAIL_MISSING", "operation": "sheets_permission_check"},
    )
    return "<email no disponible>"
