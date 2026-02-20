from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtWidgets import (
    QDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QRadioButton,
    QPushButton,
    QPlainTextEdit,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from app.application.conflicts_service import ConflictsService, ConflictRecord
from app.ui.conflict_guidance import (
    build_what_happened,
    build_why_happened,
    classify_conflict,
    delegada_name,
    recommended_action,
)


@dataclass(frozen=True)
class ConflictRow:
    record: ConflictRecord
    tipo: str
    fecha: str
    campo: str
    local_updated: str
    remote_updated: str


class ConflictsTableModel(QAbstractTableModel):
    def __init__(self, rows: list[ConflictRow]) -> None:
        super().__init__()
        self._rows = rows
        self._headers = [
            "Tipo",
            "UUID",
            "Fecha",
            "Campo clave",
            "Última edición local",
            "Última edición remota",
        ]

    def rowCount(self, parent: QModelIndex | None = None) -> int:
        return len(self._rows)

    def columnCount(self, parent: QModelIndex | None = None) -> int:
        return len(self._headers)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid() or role != Qt.DisplayRole:
            return None
        row = self._rows[index.row()]
        if index.column() == 0:
            return row.tipo
        if index.column() == 1:
            return row.record.uuid
        if index.column() == 2:
            return row.fecha
        if index.column() == 3:
            return row.campo
        if index.column() == 4:
            return row.local_updated
        if index.column() == 5:
            return row.remote_updated
        return None

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

    def set_rows(self, rows: list[ConflictRow]) -> None:
        self.beginResetModel()
        self._rows = rows
        self.endResetModel()

    def rows(self) -> list[ConflictRow]:
        return list(self._rows)


class ConflictsDialog(QDialog):
    def __init__(self, conflicts_service: ConflictsService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._conflicts_service = conflicts_service
        self._manual_review_ids: set[int] = set()
        self._resolved_count = 0
        self._table_model = ConflictsTableModel([])
        self.setWindowTitle("Resolver conflictos de sincronización")
        self._build_ui()
        self._load_conflicts()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel("Conflictos detectados")
        title.setProperty("role", "subtitle")
        layout.addWidget(title)

        self.summary_label = QLabel("Sin conflictos pendientes.")
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

        local_label = QLabel("Qué pasó")
        local_label.setProperty("role", "sectionTitle")
        compare_layout.addWidget(local_label, 0, 0)
        remote_label = QLabel("Por qué puede haber ocurrido")
        remote_label.setProperty("role", "sectionTitle")
        compare_layout.addWidget(remote_label, 0, 1)

        self.local_view = QPlainTextEdit()
        self.local_view.setReadOnly(True)
        self.remote_view = QPlainTextEdit()
        self.remote_view.setReadOnly(True)

        compare_layout.addWidget(self.local_view, 1, 0)
        compare_layout.addWidget(self.remote_view, 1, 1)
        layout.addWidget(compare_container, 2)

        options_label = QLabel("Opciones para este conflicto")
        options_label.setProperty("role", "sectionTitle")
        layout.addWidget(options_label)

        options_row = QHBoxLayout()
        self.option_keep_local = QRadioButton("Mantener local")
        self.option_keep_remote = QRadioButton("Aceptar remoto")
        self.option_manual_review = QRadioButton("Revisar manualmente")
        self.option_retry = QRadioButton("Reintentar")
        self.option_keep_local.setChecked(True)
        for radio in (
            self.option_keep_local,
            self.option_keep_remote,
            self.option_manual_review,
            self.option_retry,
        ):
            options_row.addWidget(radio)
        options_row.addStretch(1)
        layout.addLayout(options_row)

        actions = QHBoxLayout()
        actions.addStretch(1)

        self.apply_selected_button = QPushButton("Aplicar opción seleccionada")
        self.apply_selected_button.setProperty("variant", "primary")
        self.apply_selected_button.clicked.connect(self._on_apply_selected)
        actions.addWidget(self.apply_selected_button)

        self.skip_button = QPushButton("Siguiente conflicto")
        self.skip_button.setProperty("variant", "secondary")
        self.skip_button.clicked.connect(self._on_skip)
        actions.addWidget(self.skip_button)

        self.apply_all_button = QPushButton("Resolver todos automáticamente (según política por defecto)")
        self.apply_all_button.setProperty("variant", "secondary")
        self.apply_all_button.clicked.connect(self._on_apply_all)
        actions.addWidget(self.apply_all_button)

        self.policy_label = QLabel("Política activa: gana el cambio más reciente; si hay empate, se mantiene el dato local.")
        self.policy_label.setWordWrap(True)
        self.policy_label.setProperty("role", "secondary")
        layout.addWidget(self.policy_label)

        self.resolution_summary_label = QLabel("Resumen: Conflictos resueltos 0 · Pendientes 0 · Requieren revisión manual 0")
        self.resolution_summary_label.setProperty("role", "secondary")
        layout.addWidget(self.resolution_summary_label)

        layout.addLayout(actions)

    def _load_conflicts(self) -> None:
        conflicts = self._conflicts_service.list_conflicts()
        rows = [self._build_row(conflict) for conflict in conflicts]
        self._table_model.set_rows(rows)
        self._select_first()
        has_rows = bool(rows)
        self.apply_selected_button.setEnabled(has_rows)
        self.skip_button.setEnabled(has_rows)
        self.apply_all_button.setEnabled(has_rows)
        self._refresh_panel_summary(rows)
        self._refresh_resolution_summary(rows)

    def _build_row(self, conflict: ConflictRecord) -> ConflictRow:
        tipo = self._format_tipo(conflict.entity_type)
        fecha = self._extract_fecha(conflict.local_snapshot, conflict.remote_snapshot)
        campo = self._extract_campo(clone=conflict)
        local_updated = str(conflict.local_snapshot.get("updated_at") or "")
        remote_updated = str(conflict.remote_snapshot.get("updated_at") or "")
        return ConflictRow(
            record=conflict,
            tipo=tipo,
            fecha=fecha,
            campo=campo,
            local_updated=local_updated,
            remote_updated=remote_updated,
        )

    @staticmethod
    def _format_tipo(entity_type: str) -> str:
        mapping = {
            "delegadas": "delegada",
            "solicitudes": "solicitud",
            "cuadrantes": "cuadrante",
        }
        return mapping.get(entity_type, entity_type)

    @staticmethod
    def _extract_fecha(local_snapshot: dict, remote_snapshot: dict) -> str:
        for key in ("fecha_pedida", "fecha", "created_at"):
            if local_snapshot.get(key):
                return str(local_snapshot.get(key))
            if remote_snapshot.get(key):
                return str(remote_snapshot.get(key))
        return ""

    @staticmethod
    def _extract_campo(clone: ConflictRecord) -> str:
        ignored = {"id", "updated_at", "source_device", "deleted", "__row_number__"}
        local = clone.local_snapshot
        remote = clone.remote_snapshot
        for key in sorted(set(local.keys()) | set(remote.keys())):
            if key in ignored:
                continue
            if str(local.get(key)) != str(remote.get(key)):
                return key
        if clone.entity_type == "delegadas":
            return str(local.get("nombre") or remote.get("nombre") or "")
        if clone.entity_type == "solicitudes":
            return str(local.get("fecha_pedida") or remote.get("fecha") or "")
        if clone.entity_type == "cuadrantes":
            return str(local.get("dia_semana") or remote.get("dia_semana") or "")
        return ""

    def _select_first(self) -> None:
        if self._table_model.rowCount() > 0:
            self.table.selectRow(0)
        else:
            self.local_view.setPlainText("")
            self.remote_view.setPlainText("")

    def _on_selection_changed(self) -> None:
        selection = self.table.selectionModel().selectedRows()
        if not selection:
            return
        conflict = self._table_model.conflict_at(selection[0].row())
        if not conflict:
            return
        self.local_view.setPlainText(build_what_happened(conflict))
        self.remote_view.setPlainText(build_why_happened(conflict))

    def _refresh_panel_summary(self, rows: list[ConflictRow]) -> None:
        if not rows:
            self.summary_label.setText("Sin conflictos pendientes.")
            return
        first = rows[0].record
        self.summary_label.setText(
            "[Conflictos detectados]\n"
            f"- Nº total: {len(rows)}\n"
            f"- Tipo de conflicto: {classify_conflict(first)}\n"
            f"- Delegada afectada: {delegada_name(first)}\n"
            f"- Acción recomendada: {recommended_action(classify_conflict(first))}"
        )

    def _refresh_resolution_summary(self, rows: list[ConflictRow]) -> None:
        pending_ids = {row.record.id for row in rows}
        manual_pending = len(self._manual_review_ids & pending_ids)
        self.resolution_summary_label.setText(
            "Resumen: "
            f"Conflictos resueltos {self._resolved_count} · "
            f"Pendientes {len(rows)} · "
            f"Requieren revisión manual {manual_pending}"
        )

    def _current_rows(self) -> list[ConflictRow]:
        return self._table_model.rows()

    def _resolve_selected(self, keep: str) -> None:
        selection = self.table.selectionModel().selectedRows()
        if not selection:
            return
        conflict = self._table_model.conflict_at(selection[0].row())
        if not conflict:
            return
        try:
            self._conflicts_service.resolve_conflict(conflict.id, keep)
        except Exception as exc:  # pragma: no cover - fallback
            QMessageBox.critical(self, "Error", str(exc))
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
        selection = self.table.selectionModel().selectedRows()
        if not selection:
            return
        conflict = self._table_model.conflict_at(selection[0].row())
        if not conflict:
            return
        if self.option_manual_review.isChecked():
            self._manual_review_ids.add(conflict.id)
            self._on_skip()
            self._refresh_resolution_summary(self._current_rows())
            return
        if self.option_retry.isChecked():
            QMessageBox.information(self, "Reintentar", "Puedes volver a sincronizar para reintentar este conflicto.")
            self._on_skip()

    def _on_skip(self) -> None:
        row = self._next_row_index()
        if row is not None:
            self.table.selectRow(row)

    def _on_apply_all(self) -> None:
        if self._table_model.rowCount() == 0:
            return
        confirm = QMessageBox.question(
            self,
            "Aplicar a todos",
            "Se resolverán todos los conflictos con la política por defecto (gana el cambio más reciente). ¿Continuar?",
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        try:
            resolved = self._conflicts_service.resolve_all_latest()
        except Exception as exc:  # pragma: no cover - fallback
            QMessageBox.critical(self, "Error", str(exc))
            return
        self._resolved_count += resolved
        self._manual_review_ids.clear()
        self._load_conflicts()

    def _next_row_index(self) -> int | None:
        selection = self.table.selectionModel().selectedRows()
        if not selection:
            if self._table_model.rowCount() > 0:
                return 0
            return None
        row = selection[0].row() + 1
        if row >= self._table_model.rowCount():
            row = 0 if self._table_model.rowCount() > 0 else None
        return row
