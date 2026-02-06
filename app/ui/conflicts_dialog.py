from __future__ import annotations

import json
from dataclasses import dataclass

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtWidgets import (
    QDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from app.application.conflicts_service import ConflictsService, ConflictRecord


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


class ConflictsDialog(QDialog):
    def __init__(self, conflicts_service: ConflictsService, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._conflicts_service = conflicts_service
        self._table_model = ConflictsTableModel([])
        self.setWindowTitle("Revisar discrepancias")
        self._build_ui()
        self._load_conflicts()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QLabel("Discrepancias detectadas")
        title.setProperty("role", "subtitle")
        layout.addWidget(title)

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

        local_label = QLabel("Local")
        local_label.setProperty("role", "sectionTitle")
        compare_layout.addWidget(local_label, 0, 0)
        remote_label = QLabel("Remoto")
        remote_label.setProperty("role", "sectionTitle")
        compare_layout.addWidget(remote_label, 0, 1)

        self.local_view = QPlainTextEdit()
        self.local_view.setReadOnly(True)
        self.remote_view = QPlainTextEdit()
        self.remote_view.setReadOnly(True)

        compare_layout.addWidget(self.local_view, 1, 0)
        compare_layout.addWidget(self.remote_view, 1, 1)
        layout.addWidget(compare_container, 2)

        actions = QHBoxLayout()
        actions.addStretch(1)

        self.keep_local_button = QPushButton("Conservar LOCAL")
        self.keep_local_button.setProperty("variant", "primary")
        self.keep_local_button.clicked.connect(self._on_keep_local)
        actions.addWidget(self.keep_local_button)

        self.keep_remote_button = QPushButton("Conservar REMOTO")
        self.keep_remote_button.setProperty("variant", "secondary")
        self.keep_remote_button.clicked.connect(self._on_keep_remote)
        actions.addWidget(self.keep_remote_button)

        self.skip_button = QPushButton("Saltar")
        self.skip_button.setProperty("variant", "secondary")
        self.skip_button.clicked.connect(self._on_skip)
        actions.addWidget(self.skip_button)

        self.apply_all_button = QPushButton("Aplicar a todos (más reciente)")
        self.apply_all_button.setProperty("variant", "secondary")
        self.apply_all_button.clicked.connect(self._on_apply_all)
        actions.addWidget(self.apply_all_button)

        layout.addLayout(actions)

    def _load_conflicts(self) -> None:
        conflicts = self._conflicts_service.list_conflicts()
        rows = [self._build_row(conflict) for conflict in conflicts]
        self._table_model.set_rows(rows)
        self._select_first()
        has_rows = bool(rows)
        self.keep_local_button.setEnabled(has_rows)
        self.keep_remote_button.setEnabled(has_rows)
        self.skip_button.setEnabled(has_rows)
        self.apply_all_button.setEnabled(has_rows)

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
        self.local_view.setPlainText(self._pretty_json(conflict.local_snapshot))
        self.remote_view.setPlainText(self._pretty_json(conflict.remote_snapshot))

    @staticmethod
    def _pretty_json(payload: dict) -> str:
        if not payload:
            return ""
        return json.dumps(payload, indent=2, ensure_ascii=False)

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
        self._load_conflicts()

    def _on_keep_local(self) -> None:
        self._resolve_selected("local")

    def _on_keep_remote(self) -> None:
        self._resolve_selected("remote")

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
            "Se resolverán todas las discrepancias usando el dato más reciente. ¿Continuar?",
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        try:
            self._conflicts_service.resolve_all_latest()
        except Exception as exc:  # pragma: no cover - fallback
            QMessageBox.critical(self, "Error", str(exc))
            return
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
