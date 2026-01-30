from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QDoubleSpinBox,
    QWidget,
)

from app.application.dto import PersonaDTO


class PersonaDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Nueva persona")
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QFormLayout(self)

        self.nombre_input = QLineEdit()
        self.genero_input = QComboBox()
        self.genero_input.addItems(["M", "F"])
        self.horas_mes_input = QDoubleSpinBox()
        self.horas_mes_input.setRange(0, 9999)
        self.horas_mes_input.setDecimals(2)
        self.horas_ano_input = QDoubleSpinBox()
        self.horas_ano_input.setRange(0, 99999)
        self.horas_ano_input.setDecimals(2)
        self.horas_jornada_input = QDoubleSpinBox()
        self.horas_jornada_input.setRange(0, 24)
        self.horas_jornada_input.setDecimals(2)

        self.cuad_inputs = {}
        for dia in [
            ("Lunes", "cuad_lun"),
            ("Martes", "cuad_mar"),
            ("Miércoles", "cuad_mie"),
            ("Jueves", "cuad_jue"),
            ("Viernes", "cuad_vie"),
            ("Sábado", "cuad_sab"),
            ("Domingo", "cuad_dom"),
        ]:
            spin = QDoubleSpinBox()
            spin.setRange(0, 24)
            spin.setDecimals(2)
            self.cuad_inputs[dia[1]] = spin
            layout.addRow(QLabel(f"Cuadrante {dia[0]}"), spin)

        layout.addRow("Nombre", self.nombre_input)
        layout.addRow("Género", self.genero_input)
        layout.addRow("Horas mes", self.horas_mes_input)
        layout.addRow("Horas año", self.horas_ano_input)
        layout.addRow("Horas jornada defecto", self.horas_jornada_input)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_persona(self) -> PersonaDTO | None:
        if self.exec() != QDialog.Accepted:
            return None
        nombre = self.nombre_input.text().strip()
        if not nombre:
            QMessageBox.warning(self, "Validación", "El nombre es obligatorio.")
            return None
        return PersonaDTO(
            id=None,
            nombre=nombre,
            genero=self.genero_input.currentText(),
            horas_mes=self.horas_mes_input.value(),
            horas_ano=self.horas_ano_input.value(),
            horas_jornada_defecto=self.horas_jornada_input.value(),
            cuad_lun=self.cuad_inputs["cuad_lun"].value(),
            cuad_mar=self.cuad_inputs["cuad_mar"].value(),
            cuad_mie=self.cuad_inputs["cuad_mie"].value(),
            cuad_jue=self.cuad_inputs["cuad_jue"].value(),
            cuad_vie=self.cuad_inputs["cuad_vie"].value(),
            cuad_sab=self.cuad_inputs["cuad_sab"].value(),
            cuad_dom=self.cuad_inputs["cuad_dom"].value(),
        )
