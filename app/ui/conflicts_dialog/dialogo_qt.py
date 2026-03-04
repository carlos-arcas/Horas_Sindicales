from __future__ import annotations

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtWidgets import (
    QDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QRadioButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from app.application.conflicts_service import ConflictsService, ConflictRecord
from app.ui.conflict_guidance import build_what_happened, build_why_happened

from .adaptador_i18n import t
from .contratos import ViewModelConflictoFila
from .presenter_conflictos import (
    construir_filas_conflicto,
    construir_resumen_panel_inicial,
    construir_resumen_resolucion,
    siguiente_indice,
)


class ConflictsTableModel(QAbstractTableModel):
    def __init__(self, rows: list[ViewModelConflictoFila]) -> None:
        super().__init__()
        self._rows = rows
        self._headers = [
            t("ui.conflictos.columna_tipo"),
            "UUID",
            t("ui.conflictos.columna_fecha"),
            t("ui.conflictos.columna_campo_clave"),
            t("ui.conflictos.columna_ultima_edicion_local"),
            t("ui.conflictos.columna_ultima_edicion_remota"),
        ]

    def rowCount(self, parent: QModelIndex | None = None) -> int:
        return len(self._rows)

    def columnCount(self, parent: QModelIndex | None = None) -> int:
        return len(self._headers)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid() or role != Qt.DisplayRole:
            return None
        row = self._rows[index.row()]
        columnas = {
            0: row.tipo,
            1: row.record.uuid,
            2: row.fecha,
            3: row.campo,
            4: row.local_updated,
            5: row.remote_updated,
        }
        return columnas.get(index.column())

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            return self._headers[section]
        return str(section + 1)

    def conflict_at(self, row: int) -> ConflictRecord | None:
        if 0 <= row < len(self._rows):
            return self._rows[row].record
        return None

    def set_rows(self, rows: list[ViewModelConflictoFila]) -> None:
        self.beginResetModel()
        self._rows = rows
        self.endResetModel()

    def rows(self) -> list[ViewModelConflictoFila]:
        return list(self._rows)


class ConflictsDialog(QDialog):
    def __init__(self, conflicts_service: ConflictsService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._conflicts_service = conflicts_service
        self._manual_review_ids: set[int] = set()
        self._resolved_count = 0
        self._table_model = ConflictsTableModel([])
        self.setWindowTitle(t("ui.conflictos.titulo_resolver"))
        self._build_ui()
        self._load_conflicts()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel(t("ui.conflictos.conflictos_detectados"))
        title.setProperty("role", "subtitle")
        layout.addWidget(title)

        self.summary_label = QLabel(t("ui.conflictos.sin_conflictos_pendientes"))
        self.summary_label.setProperty("role", "secondary")
        self.summary_label.setWordWrap(True)
        layout.addWidget(self.summary_label)

        self.table = QTableView()
        self.table.setModel(self._table_model)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setSelectionMode(QTableView.SingleSelection)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        self.table.selectionModel().selectionChanged.connect(self._on_selection_changed)
        layout.addWidget(self.table, 1)

        compare_container = QWidget()
        compare_layout = QGridLayout(compare_container)
        compare_layout.setContentsMargins(0, 0, 0, 0)
        compare_layout.setSpacing(8)

        local_label = QLabel(t("ui.conflictos.que_paso"))
        local_label.setProperty("role", "sectionTitle")
        compare_layout.addWidget(local_label, 0, 0)
        remote_label = QLabel(t("ui.conflictos.por_que_puede_haber_ocurrido"))
        remote_label.setProperty("role", "sectionTitle")
        compare_layout.addWidget(remote_label, 0, 1)

        self.local_view = QPlainTextEdit()
        self.local_view.setReadOnly(True)
        self.remote_view = QPlainTextEdit()
        self.remote_view.setReadOnly(True)

        compare_layout.addWidget(self.local_view, 1, 0)
        compare_layout.addWidget(self.remote_view, 1, 1)
        layout.addWidget(compare_container, 2)

        options_label = QLabel(t("ui.conflictos.opciones_para_conflicto"))
        options_label.setProperty("role", "sectionTitle")
        layout.addWidget(options_label)

        options_row = QHBoxLayout()
        self.option_keep_local = QRadioButton(t("ui.conflictos.mantener_local"))
        self.option_keep_remote = QRadioButton(t("ui.conflictos.aceptar_remoto"))
        self.option_manual_review = QRadioButton(t("ui.conflictos.revisar_manualmente"))
        self.option_retry = QRadioButton(t("ui.comun.reintentar"))
        self.option_keep_local.setChecked(True)
        for radio in self._opciones_conflicto():
            options_row.addWidget(radio)
        options_row.addStretch(1)
        layout.addLayout(options_row)

        actions = QHBoxLayout()
        actions.addStretch(1)

        self.apply_selected_button = QPushButton(t("ui.conflictos.aplicar_opcion_seleccionada"))
        self.apply_selected_button.setProperty("variant", "primary")
        self.apply_selected_button.clicked.connect(self._on_apply_selected)
        actions.addWidget(self.apply_selected_button)

        self.skip_button = QPushButton(t("ui.conflictos.siguiente_conflicto"))
        self.skip_button.setProperty("variant", "secondary")
        self.skip_button.clicked.connect(self._on_skip)
        actions.addWidget(self.skip_button)

        self.apply_all_button = QPushButton(t("ui.conflictos.resolver_todos_automaticamente"))
        self.apply_all_button.setProperty("variant", "secondary")
        self.apply_all_button.clicked.connect(self._on_apply_all)
        actions.addWidget(self.apply_all_button)

        self.policy_label = QLabel(t("ui.conflictos.politica_activa"))
        self.policy_label.setWordWrap(True)
        self.policy_label.setProperty("role", "secondary")
        layout.addWidget(self.policy_label)

        self.resolution_summary_label = QLabel(
            t("ui.conflictos.resumen_conflictos_resueltos").format(resueltos=0, pendientes=0, revision_manual=0)
        )
        self.resolution_summary_label.setProperty("role", "secondary")
        layout.addWidget(self.resolution_summary_label)

        layout.addLayout(actions)

    def _opciones_conflicto(self) -> tuple[QRadioButton, ...]:
        return (
            self.option_keep_local,
            self.option_keep_remote,
            self.option_manual_review,
            self.option_retry,
        )

    def _load_conflicts(self) -> None:
        rows = construir_filas_conflicto(self._conflicts_service.list_conflicts())
        self._table_model.set_rows(rows)
        self._select_first()
        has_rows = bool(rows)
        self.apply_selected_button.setEnabled(has_rows)
        self.skip_button.setEnabled(has_rows)
        self.apply_all_button.setEnabled(has_rows)
        self._refresh_panel_summary(rows)
        self._refresh_resolution_summary(rows)

    def _select_first(self) -> None:
        if self._table_model.rowCount() > 0:
            self.table.selectRow(0)
            return
        self.local_view.setPlainText("")
        self.remote_view.setPlainText("")

    def _on_selection_changed(self) -> None:
        conflict = self._selected_conflict()
        if not conflict:
            return
        self.local_view.setPlainText(build_what_happened(conflict))
        self.remote_view.setPlainText(build_why_happened(conflict))

    def _refresh_panel_summary(self, rows: list[ViewModelConflictoFila]) -> None:
        self.summary_label.setText(construir_resumen_panel_inicial(rows, t))

    def _refresh_resolution_summary(self, rows: list[ViewModelConflictoFila]) -> None:
        resumen = construir_resumen_resolucion(rows, self._manual_review_ids, self._resolved_count)
        self.resolution_summary_label.setText(
            t("ui.conflictos.resumen_conflictos_resueltos").format(
                resueltos=resumen.resueltos,
                pendientes=resumen.pendientes,
                revision_manual=resumen.revision_manual,
            )
        )

    def _current_rows(self) -> list[ViewModelConflictoFila]:
        return self._table_model.rows()

    def _selected_conflict(self) -> ConflictRecord | None:
        selection = self.table.selectionModel().selectedRows()
        if not selection:
            return None
        return self._table_model.conflict_at(selection[0].row())

    def _resolve_selected(self, keep: str) -> None:
        conflict = self._selected_conflict()
        if not conflict:
            return
        try:
            self._conflicts_service.resolve_conflict(conflict.id, keep)
        except Exception as exc:  # pragma: no cover - fallback
            QMessageBox.critical(self, t("ui.validacion.error"), str(exc))
            return
        self._resolved_count += 1
        self._manual_review_ids.discard(conflict.id)
        self._load_conflicts()

    def _on_apply_selected(self) -> None:
        if self.option_keep_local.isChecked():
            self._resolve_selected("local")
            return
        if self.option_keep_remote.isChecked():
            self._resolve_selected("remote")
            return
        conflict = self._selected_conflict()
        if not conflict:
            return
        if self.option_manual_review.isChecked():
            self._manual_review_ids.add(conflict.id)
            self._on_skip()
            self._refresh_resolution_summary(self._current_rows())
            return
        if self.option_retry.isChecked():
            QMessageBox.information(self, t("ui.comun.reintentar"), t("ui.conflictos.conflicto_pendiente_reintentar"))
            self._on_skip()

    def _on_skip(self) -> None:
        selection = self.table.selectionModel().selectedRows()
        actual = selection[0].row() if selection else None
        siguiente = siguiente_indice(actual, self._table_model.rowCount())
        if siguiente is not None:
            self.table.selectRow(siguiente)

    def _on_apply_all(self) -> None:
        if self._table_model.rowCount() == 0:
            return
        confirm = QMessageBox.question(self, t("ui.conflictos.aplicar_a_todos"), t("ui.conflictos.confirmacion_aplicar_a_todos"))
        if confirm != QMessageBox.StandardButton.Yes:
            return
        try:
            resolved = self._conflicts_service.resolve_all_latest()
        except Exception as exc:  # pragma: no cover - fallback
            QMessageBox.critical(self, t("ui.validacion.error"), str(exc))
            return
        self._resolved_count += resolved
        self._manual_review_ids.clear()
        self._load_conflicts()
