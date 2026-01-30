from __future__ import annotations

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt

from app.application.dto import PersonaDTO


class PersonasTableModel(QAbstractTableModel):
    def __init__(self, personas: list[PersonaDTO] | None = None) -> None:
        super().__init__()
        self._personas = personas or []
        self._headers = [
            "Nombre",
            "Género",
            "Horas mes",
            "Horas año",
            "Horas jornada",
        ]

    def rowCount(self, parent: QModelIndex | None = None) -> int:
        return len(self._personas)

    def columnCount(self, parent: QModelIndex | None = None) -> int:
        return len(self._headers)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid() or role != Qt.DisplayRole:
            return None
        persona = self._personas[index.row()]
        column = index.column()
        if column == 0:
            return persona.nombre
        if column == 1:
            return persona.genero
        if column == 2:
            return f"{persona.horas_mes:.2f}"
        if column == 3:
            return f"{persona.horas_ano:.2f}"
        if column == 4:
            return f"{persona.horas_jornada_defecto:.2f}"
        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            return self._headers[section]
        return str(section + 1)

    def set_personas(self, personas: list[PersonaDTO]) -> None:
        self.beginResetModel()
        self._personas = personas
        self.endResetModel()

    def persona_at(self, row: int) -> PersonaDTO | None:
        if 0 <= row < len(self._personas):
            return self._personas[row]
        return None
