from __future__ import annotations

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt

from app.application.dto import PersonaDTO, SolicitudDTO


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


class SolicitudesTableModel(QAbstractTableModel):
    def __init__(self, solicitudes: list[SolicitudDTO] | None = None) -> None:
        super().__init__()
        self._solicitudes = solicitudes or []
        self._headers = [
            "Fecha pedida",
            "Desde",
            "Hasta",
            "Completo",
            "Horas",
        ]

    def rowCount(self, parent: QModelIndex | None = None) -> int:
        return len(self._solicitudes)

    def columnCount(self, parent: QModelIndex | None = None) -> int:
        return len(self._headers)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid() or role != Qt.DisplayRole:
            return None
        solicitud = self._solicitudes[index.row()]
        column = index.column()
        if column == 0:
            return solicitud.fecha_pedida
        if column == 1:
            return solicitud.desde or "-"
        if column == 2:
            return solicitud.hasta or "-"
        if column == 3:
            return "Sí" if solicitud.completo else "No"
        if column == 4:
            return f"{solicitud.horas:.2f}"
        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            return self._headers[section]
        return str(section + 1)

    def set_solicitudes(self, solicitudes: list[SolicitudDTO]) -> None:
        self.beginResetModel()
        self._solicitudes = solicitudes
        self.endResetModel()

    def solicitud_at(self, row: int) -> SolicitudDTO | None:
        if 0 <= row < len(self._solicitudes):
            return self._solicitudes[row]
        return None

    def append_solicitud(self, solicitud: SolicitudDTO) -> None:
        row = len(self._solicitudes)
        self.beginInsertRows(QModelIndex(), row, row)
        self._solicitudes.append(solicitud)
        self.endInsertRows()

    def clear(self) -> None:
        self.beginResetModel()
        self._solicitudes = []
        self.endResetModel()
