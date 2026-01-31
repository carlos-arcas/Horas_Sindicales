from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QWidget,
)

from app.application.dto import PersonaDTO
from app.domain.time_utils import minutes_to_hhmm
from app.ui.widgets.time_edit import TimeEditHM


class PersonaDialog(QDialog):
    def __init__(self, parent: QWidget | None = None, persona: PersonaDTO | None = None) -> None:
        super().__init__(parent)
        self._persona = persona
        self.setWindowTitle("Editar delegado" if persona else "Nuevo delegado")
        self._build_ui()
        if persona:
            self._load_persona(persona)

    def _build_ui(self) -> None:
        layout = QFormLayout(self)

        self.nombre_input = QLineEdit()
        self.genero_input = QComboBox()
        self.genero_input.addItems(["M", "F"])
        self.horas_mes_input = TimeEditHM()
        self.horas_mes_input.set_hour_range(0, 9999)
        self.horas_ano_input = TimeEditHM()
        self.horas_ano_input.set_hour_range(0, 99999)

        layout.addRow("Nombre", self.nombre_input)
        layout.addRow("Género", self.genero_input)
        layout.addRow("Horas mes", self.horas_mes_input)
        layout.addRow("Horas año", self.horas_ano_input)

        self.cuad_inputs = {}
        self.cuad_totals = {}
        for dia in [
            ("Lunes", "cuad_lun"),
            ("Martes", "cuad_mar"),
            ("Miércoles", "cuad_mie"),
            ("Jueves", "cuad_jue"),
            ("Viernes", "cuad_vie"),
            ("Sábado", "cuad_sab"),
            ("Domingo", "cuad_dom"),
        ]:
            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(8)

            man_label = QLabel("Mañana")
            man_input = TimeEditHM()
            man_input.set_hour_range(0, 24)
            tar_label = QLabel("Tarde")
            tar_input = TimeEditHM()
            tar_input.set_hour_range(0, 24)
            total_label = QLabel("Total: 00:00")
            total_label.setProperty("role", "secondary")

            row_layout.addWidget(man_label)
            row_layout.addWidget(man_input)
            row_layout.addWidget(tar_label)
            row_layout.addWidget(tar_input)
            row_layout.addWidget(total_label)
            row_layout.addStretch(1)

            self.cuad_inputs[dia[1]] = {"man": man_input, "tar": tar_input}
            self.cuad_totals[dia[1]] = total_label
            man_input.minutesChanged.connect(
                lambda _value, key=dia[1]: self._update_total_label(key)
            )
            tar_input.minutesChanged.connect(
                lambda _value, key=dia[1]: self._update_total_label(key)
            )
            layout.addRow(QLabel(f"Cuadrante {dia[0]}"), row_widget)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        ok_button = buttons.button(QDialogButtonBox.Ok)
        if ok_button:
            ok_button.setProperty("variant", "primary")
        cancel_button = buttons.button(QDialogButtonBox.Cancel)
        if cancel_button:
            cancel_button.setProperty("variant", "secondary")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def _load_persona(self, persona: PersonaDTO) -> None:
        self.nombre_input.setText(persona.nombre)
        self.nombre_input.setReadOnly(True)
        self.genero_input.setCurrentText(persona.genero)
        self.horas_mes_input.set_minutes(persona.horas_mes)
        self.horas_ano_input.set_minutes(persona.horas_ano)
        self.cuad_inputs["cuad_lun"]["man"].set_minutes(persona.cuad_lun_man_min)
        self.cuad_inputs["cuad_lun"]["tar"].set_minutes(persona.cuad_lun_tar_min)
        self.cuad_inputs["cuad_mar"]["man"].set_minutes(persona.cuad_mar_man_min)
        self.cuad_inputs["cuad_mar"]["tar"].set_minutes(persona.cuad_mar_tar_min)
        self.cuad_inputs["cuad_mie"]["man"].set_minutes(persona.cuad_mie_man_min)
        self.cuad_inputs["cuad_mie"]["tar"].set_minutes(persona.cuad_mie_tar_min)
        self.cuad_inputs["cuad_jue"]["man"].set_minutes(persona.cuad_jue_man_min)
        self.cuad_inputs["cuad_jue"]["tar"].set_minutes(persona.cuad_jue_tar_min)
        self.cuad_inputs["cuad_vie"]["man"].set_minutes(persona.cuad_vie_man_min)
        self.cuad_inputs["cuad_vie"]["tar"].set_minutes(persona.cuad_vie_tar_min)
        self.cuad_inputs["cuad_sab"]["man"].set_minutes(persona.cuad_sab_man_min)
        self.cuad_inputs["cuad_sab"]["tar"].set_minutes(persona.cuad_sab_tar_min)
        self.cuad_inputs["cuad_dom"]["man"].set_minutes(persona.cuad_dom_man_min)
        self.cuad_inputs["cuad_dom"]["tar"].set_minutes(persona.cuad_dom_tar_min)
        for key in self.cuad_inputs:
            self._update_total_label(key)

    def _update_total_label(self, key: str) -> None:
        total = self.cuad_inputs[key]["man"].minutes() + self.cuad_inputs[key]["tar"].minutes()
        self.cuad_totals[key].setText(f"Total: {minutes_to_hhmm(total)}")

    def get_persona(self) -> PersonaDTO | None:
        if self.exec() != QDialog.DialogCode.Accepted:
            return None
        nombre = self.nombre_input.text().strip()
        if not nombre:
            QMessageBox.warning(self, "Validación", "El nombre es obligatorio.")
            return None
        return PersonaDTO(
            id=self._persona.id if self._persona else None,
            nombre=nombre,
            genero=self.genero_input.currentText(),
            horas_mes=self.horas_mes_input.minutes(),
            horas_ano=self.horas_ano_input.minutes(),
            is_active=self._persona.is_active if self._persona else True,
            cuad_lun_man_min=self.cuad_inputs["cuad_lun"]["man"].minutes(),
            cuad_lun_tar_min=self.cuad_inputs["cuad_lun"]["tar"].minutes(),
            cuad_mar_man_min=self.cuad_inputs["cuad_mar"]["man"].minutes(),
            cuad_mar_tar_min=self.cuad_inputs["cuad_mar"]["tar"].minutes(),
            cuad_mie_man_min=self.cuad_inputs["cuad_mie"]["man"].minutes(),
            cuad_mie_tar_min=self.cuad_inputs["cuad_mie"]["tar"].minutes(),
            cuad_jue_man_min=self.cuad_inputs["cuad_jue"]["man"].minutes(),
            cuad_jue_tar_min=self.cuad_inputs["cuad_jue"]["tar"].minutes(),
            cuad_vie_man_min=self.cuad_inputs["cuad_vie"]["man"].minutes(),
            cuad_vie_tar_min=self.cuad_inputs["cuad_vie"]["tar"].minutes(),
            cuad_sab_man_min=self.cuad_inputs["cuad_sab"]["man"].minutes(),
            cuad_sab_tar_min=self.cuad_inputs["cuad_sab"]["tar"].minutes(),
            cuad_dom_man_min=self.cuad_inputs["cuad_dom"]["man"].minutes(),
            cuad_dom_tar_min=self.cuad_inputs["cuad_dom"]["tar"].minutes(),
        )
