from __future__ import annotations

from pathlib import Path

try:
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication, QDialog, QHBoxLayout, QMessageBox, QPlainTextEdit, QPushButton, QTreeWidget, QTreeWidgetItem, QVBoxLayout
except Exception:  # pragma: no cover - habilita import en CI sin Qt
    QApplication = QDialog = QHBoxLayout = QMessageBox = QPlainTextEdit = QPushButton = QTreeWidget = QTreeWidgetItem = QVBoxLayout = object
    Qt = object

from app.domain.sync_models import SyncSummary
from app.ui.patterns import STATUS_PATTERNS, apply_modal_behavior, status_badge
from app.ui.sync_reporting import list_sync_history, load_sync_report, persist_report, to_markdown
from app.ui.toast_helpers import toast_success


def apply_sync_report(ventana, report) -> None:
    ventana._last_sync_report = report
    ventana._sync_attempts.append({"status": report.status, "counts": report.counts})
    counts = report.counts
    set_sync_status_badge(ventana, report.status)
    ventana.sync_source_label.setText(f"Fuente: {report.source}")
    ventana.sync_scope_label.setText(f"Rango: {report.scope}")
    ventana.sync_idempotency_label.setText(f"Evita duplicados: {report.idempotency_criteria}")
    ventana.sync_counts_label.setText(
        "Resumen: "
        f"Filas creadas: {counts.get('created', 0)} · "
        f"Filas actualizadas: {counts.get('updated', 0)} · "
        f"Filas omitidas: {counts.get('skipped', 0)} · "
        f"Conflictos: {counts.get('conflicts', 0)} · "
        f"Errores: {counts.get('errors', 0)}"
    )
    ventana.sync_panel_status.setText(
        f"Estado: intento #{len(ventana._sync_attempts)} · actual {status_to_label(report.status)} · final {status_to_label(report.final_status)}"
    )
    ventana.last_sync_metrics_label.setText(
        f"Duración: {report.duration_ms} ms · Cambios: {counts.get('created', 0) + counts.get('updated', 0)} · "
        f"Conflictos: {report.conflicts_count} · Errores: {report.error_count}"
    )
    ventana._refresh_sync_trend_label()
    ventana.go_to_sync_config_button.setVisible(report.status == "CONFIG_INCOMPLETE")
    ventana.sync_details_button.setEnabled(True)
    ventana.copy_sync_report_button.setEnabled(True)
    ventana.retry_failed_button.setEnabled(bool(report.errors or report.conflicts))
    ventana.review_conflicts_button.setText("Revisar conflictos" if report.conflicts_count > 0 else "Revisar conflictos (sin pendientes)")
    ventana._update_conflicts_reminder()
    persist_report(report, Path.cwd())
    ventana._refresh_health_and_alerts()


def on_show_sync_history(ventana) -> None:
    history = list_sync_history(Path.cwd())
    if not history:
        ventana.toast.info("No hay sincronizaciones históricas disponibles.", title="Histórico")
        return
    dialog = QDialog(ventana)
    dialog.setWindowTitle("Histórico de sincronizaciones")
    dialog.resize(800, 420)
    layout = QVBoxLayout(dialog)
    table = QTreeWidget(dialog)
    table.setColumnCount(4)
    table.setHeaderLabels(["Archivo", "Sync ID", "Estado", "Intentos"])
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
    open_btn = QPushButton("Abrir detalle")
    open_btn.clicked.connect(_open_selected)
    copy_btn = QPushButton("Copiar informe")
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
    dialog.setWindowTitle("Detalles de sincronización")
    dialog.resize(940, 480)
    apply_modal_behavior(dialog)
    layout = QVBoxLayout(dialog)
    table = QTreeWidget(dialog)
    table.setColumnCount(6)
    table.setHeaderLabels(["Timestamp", "Sev", "Entidad", "Mensaje", "Acción sugerida", "Sección"])
    for entry in report.entries:
        item = QTreeWidgetItem([entry.timestamp, entry.severity, entry.entity, entry.message, entry.suggested_action, entry.section])
        table.addTopLevelItem(item)
    table.header().setStretchLastSection(True)
    layout.addWidget(table, 1)

    actions = QHBoxLayout()
    open_affected = QPushButton("Abrir solicitud afectada")
    open_affected.setProperty("variant", "secondary")
    open_affected.setEnabled(bool(report.conflicts))
    open_affected.clicked.connect(ventana._on_review_conflicts)
    actions.addWidget(open_affected)

    mark_review = QPushButton("Marcar para revisión")
    mark_review.setProperty("variant", "secondary")
    mark_review.setEnabled(bool(report.conflicts))
    mark_review.clicked.connect(lambda: ventana.toast.info("Registro marcado para revisión manual."))
    actions.addWidget(mark_review)

    retry_failed = QPushButton("Reintentar solo fallidos")
    retry_failed.setProperty("variant", "secondary")
    retry_failed.setEnabled(bool(report.errors or report.conflicts))
    retry_failed.clicked.connect(ventana._on_retry_failed)
    actions.addWidget(retry_failed)

    export_detail = QPushButton("Exportar detalle")
    export_detail.setProperty("variant", "secondary")
    export_detail.clicked.connect(ventana._on_copy_sync_report)
    actions.addWidget(export_detail)

    close_button = QPushButton("Cerrar")
    close_button.setProperty("variant", "ghost")
    close_button.clicked.connect(dialog.accept)
    actions.addWidget(close_button)
    layout.addLayout(actions)
    dialog.exec()


def set_sync_status_badge(ventana, status: str) -> None:
    ventana.sync_status_badge.setText(status_to_label(status))
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
        "IDLE": "⏸ En espera",
        "RUNNING": "🕒 Pendiente · Sincronizando",
        "OK": status_badge("CONFIRMED"),
        "OK_WARN": status_badge("WARNING"),
        "ERROR": status_badge("ERROR"),
        "CONFIG_INCOMPLETE": "⛔ Error · Configuración incompleta",
    }.get(status, status)


def sync_source_text(ventana) -> str:
    config = ventana._sheets_service.get_config()
    if not config:
        return "Error: configura credenciales de Google Sheets"
    credentials_name = Path(config.credentials_path).name if config.credentials_path else "sin archivo"
    sheet_short = f"…{config.spreadsheet_id[-6:]}" if config.spreadsheet_id else "sin-id"
    return f"Spreadsheet {sheet_short} · credencial {credentials_name}"


def sync_scope_text() -> str:
    return "Sincronización completa de delegadas y solicitudes."


def sync_actor_text(ventana) -> str:
    persona = ventana._current_persona()
    return persona.nombre if persona is not None else "Delegada no seleccionada"


def show_sync_summary_dialog(ventana, title: str, summary: SyncSummary) -> None:
    last_sync = ventana._sync_service.get_last_sync_at()
    last_sync_text = ventana._format_timestamp(last_sync) if last_sync else "Nunca"
    message = (
        f"Insertadas en local: {summary.inserted_local}\n"
        f"Actualizadas en local: {summary.updated_local}\n"
        f"Insertadas en Sheets: {summary.inserted_remote}\n"
        f"Actualizadas en Sheets: {summary.updated_remote}\n"
        f"Duplicados omitidos: {summary.duplicates_skipped}\n"
        f"Omitidas por delegada: {summary.omitted_by_delegada}\n"
        f"Conflictos: {summary.conflicts_detected}\n"
        f"Errores: {summary.errors}\n"
        f"Última sincronización: {last_sync_text}"
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
    dialog = QMessageBox(ventana)
    dialog.setWindowTitle(title)
    dialog.setIcon(icon)
    dialog.setText(message)
    action_mapping: dict[object, object] = {}
    for label, callback in action_buttons:
        button = dialog.addButton(label, QMessageBox.ActionRole)
        action_mapping[button] = callback
    details_button = None
    if details:
        details_button = dialog.addButton("Ver detalles", QMessageBox.ActionRole)
    dialog.addButton("Cerrar", QMessageBox.AcceptRole)
    dialog.exec()
    clicked_button = dialog.clickedButton()
    if clicked_button in action_mapping:
        action_mapping[clicked_button]()
        return
    if details_button and clicked_button == details_button:
        show_details_dialog(ventana, title, details)


def show_details_dialog(ventana, title: str, details: str) -> None:
    dialog = QDialog(ventana)
    dialog.setWindowTitle(title)
    apply_modal_behavior(dialog)
    layout = QVBoxLayout(dialog)
    details_text = QPlainTextEdit()
    details_text.setReadOnly(True)
    details_text.setPlainText(details)
    layout.addWidget(details_text)
    close_button = QPushButton("Cerrar")
    close_button.setProperty("variant", "ghost")
    close_button.clicked.connect(dialog.accept)
    layout.addWidget(close_button, alignment=Qt.AlignRight)
    dialog.resize(520, 360)
    dialog.exec()


def service_account_email(ventana) -> str | None:
    config = ventana._sheets_service.get_config()
    if config is None:
        return None
    account_email = getattr(config, "service_account_email", None)
    if isinstance(account_email, str) and account_email.strip():
        return account_email.strip()
    return None
