from __future__ import annotations

from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QRadioButton,
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
        else:
            self._set_uniform_mode(True)
            self._set_weekend_enabled(False)

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

        mode_widget = QWidget()
        mode_layout = QHBoxLayout(mode_widget)
        mode_layout.setContentsMargins(0, 0, 0, 0)
        mode_layout.setSpacing(12)
        self.uniform_radio = QRadioButton("Mismo cuadrante todos los días")
        self.by_day_radio = QRadioButton("Horarios distintos por día")
        self.mode_group = QButtonGroup(self)
        self.mode_group.addButton(self.uniform_radio)
        self.mode_group.addButton(self.by_day_radio)
        mode_layout.addWidget(self.uniform_radio)
        mode_layout.addWidget(self.by_day_radio)
        mode_layout.addStretch(1)
        layout.addRow("Modo cuadrante L-V", mode_widget)

        self.uniform_row = self._build_day_row("Cuadrante base L-V")
        layout.addRow("Cuadrante L-V", self.uniform_row["widget"])

        self.trabaja_finde_check = QCheckBox("Trabaja fines de semana")
        layout.addRow("Fines de semana", self.trabaja_finde_check)

        self.cuad_inputs: dict[str, dict[str, TimeEditHM]] = {}
        self.cuad_totals: dict[str, QLabel] = {}
        self._weekday_keys = ["cuad_lun", "cuad_mar", "cuad_mie", "cuad_jue", "cuad_vie"]

        self.weekdays_widget = QWidget()
        weekdays_layout = QFormLayout(self.weekdays_widget)
        weekdays_layout.setContentsMargins(0, 0, 0, 0)
        weekdays_layout.setSpacing(8)
        for day_label, day_key in [
            ("Lunes", "cuad_lun"),
            ("Martes", "cuad_mar"),
            ("Miércoles", "cuad_mie"),
            ("Jueves", "cuad_jue"),
            ("Viernes", "cuad_vie"),
        ]:
            row = self._build_day_row(day_label)
            self.cuad_inputs[day_key] = {"man": row["man"], "tar": row["tar"]}
            self.cuad_totals[day_key] = row["total"]
            weekdays_layout.addRow(QLabel(day_label), row["widget"])
        layout.addRow("Cuadrante por día", self.weekdays_widget)

        self.weekend_container = QWidget()
        weekend_container_layout = QVBoxLayout(self.weekend_container)
        weekend_container_layout.setContentsMargins(0, 0, 0, 0)
        weekend_container_layout.setSpacing(6)

        weekend_title = QLabel("Cuadrante fin de semana")
        weekend_title.setProperty("role", "sectionTitle")
        weekend_container_layout.addWidget(weekend_title)

        self.weekend_widget = QWidget()
        weekend_layout = QFormLayout(self.weekend_widget)
        weekend_layout.setContentsMargins(0, 0, 0, 0)
        weekend_layout.setSpacing(8)
        for day_label, day_key in [("Sábado", "cuad_sab"), ("Domingo", "cuad_dom")]:
            row = self._build_day_row(day_label)
            self.cuad_inputs[day_key] = {"man": row["man"], "tar": row["tar"]}
            self.cuad_totals[day_key] = row["total"]
            weekend_layout.addRow(QLabel(day_label), row["widget"])
        weekend_container_layout.addWidget(self.weekend_widget)
        layout.addRow(self.weekend_container)
        self.weekend_container.setVisible(False)

        self.uniform_radio.toggled.connect(self._on_mode_toggled)
        self.by_day_radio.toggled.connect(self._on_mode_toggled)
        self.trabaja_finde_check.toggled.connect(self._on_weekend_toggled)

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

    def _build_day_row(self, _label: str) -> dict[str, QWidget | TimeEditHM | QLabel]:
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

        key = f"temp_{id(row_widget)}"
        man_input.minutesChanged.connect(lambda _value, day_key=key, man=man_input, tar=tar_input, total=total_label: self._update_total_for_controls(day_key, man, tar, total))
        tar_input.minutesChanged.connect(lambda _value, day_key=key, man=man_input, tar=tar_input, total=total_label: self._update_total_for_controls(day_key, man, tar, total))

        return {"widget": row_widget, "man": man_input, "tar": tar_input, "total": total_label}

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

        self.uniform_row["man"].set_minutes(persona.cuad_lun_man_min)
        self.uniform_row["tar"].set_minutes(persona.cuad_lun_tar_min)

        for key in self.cuad_inputs:
            self._update_total_label(key)
        self._update_total_for_controls(
            "uniform",
            self.uniform_row["man"],
            self.uniform_row["tar"],
            self.uniform_row["total"],
        )

        self.trabaja_finde_check.setChecked(persona.trabaja_finde)

        uniform_detectado = persona.cuadrante_uniforme or self._weekdays_are_uniform(
            persona.cuad_lun_man_min,
            persona.cuad_lun_tar_min,
            persona.cuad_mar_man_min,
            persona.cuad_mar_tar_min,
            persona.cuad_mie_man_min,
            persona.cuad_mie_tar_min,
            persona.cuad_jue_man_min,
            persona.cuad_jue_tar_min,
            persona.cuad_vie_man_min,
            persona.cuad_vie_tar_min,
        )
        self._set_uniform_mode(uniform_detectado)
        self._set_weekend_enabled(persona.trabaja_finde)

    def _on_mode_toggled(self) -> None:
        self._set_uniform_mode(self.uniform_radio.isChecked())

    def _set_uniform_mode(self, enabled: bool) -> None:
        self.uniform_radio.blockSignals(True)
        self.by_day_radio.blockSignals(True)
        self.uniform_radio.setChecked(enabled)
        self.by_day_radio.setChecked(not enabled)
        self.uniform_radio.blockSignals(False)
        self.by_day_radio.blockSignals(False)

        self.uniform_row["widget"].setVisible(enabled)
        self.weekdays_widget.setVisible(not enabled)

    def _on_weekend_toggled(self) -> None:
        self._set_weekend_enabled(self.trabaja_finde_check.isChecked())

    def _set_weekend_enabled(self, enabled: bool) -> None:
        self.weekend_container.setVisible(enabled)

    def _weekdays_are_uniform(self, *values: int) -> bool:
        if len(values) != 10:
            return False
        lunes = values[0:2]
        for idx in range(2, 10, 2):
            if (values[idx], values[idx + 1]) != lunes:
                return False
        return True

    def _update_total_for_controls(
        self,
        _key: str,
        man_input: TimeEditHM,
        tar_input: TimeEditHM,
        total_label: QLabel,
    ) -> None:
        total = man_input.minutes() + tar_input.minutes()
        total_label.setText(f"Total: {minutes_to_hhmm(total)}")

    def _update_total_label(self, key: str) -> None:
        total = self.cuad_inputs[key]["man"].minutes() + self.cuad_inputs[key]["tar"].minutes()
        self.cuad_totals[key].setText(f"Total: {minutes_to_hhmm(total)}")

    def _weekday_values(self) -> dict[str, tuple[int, int]]:
        if self.uniform_radio.isChecked():
            man = self.uniform_row["man"].minutes()
            tar = self.uniform_row["tar"].minutes()
            return {key: (man, tar) for key in self._weekday_keys}
        return {
            key: (
                self.cuad_inputs[key]["man"].minutes(),
                self.cuad_inputs[key]["tar"].minutes(),
            )
            for key in self._weekday_keys
        }

    def get_persona(self) -> PersonaDTO | None:
        if self.exec() != QDialog.DialogCode.Accepted:
            return None
        nombre = self.nombre_input.text().strip()
        if not nombre:
            QMessageBox.warning(self, "Validación", "El nombre es obligatorio.")
            return None

        weekdays = self._weekday_values()

        return PersonaDTO(
            id=self._persona.id if self._persona else None,
            nombre=nombre,
            genero=self.genero_input.currentText(),
            horas_mes=self.horas_mes_input.minutes(),
            horas_ano=self.horas_ano_input.minutes(),
            is_active=self._persona.is_active if self._persona else True,
            cuad_lun_man_min=weekdays["cuad_lun"][0],
            cuad_lun_tar_min=weekdays["cuad_lun"][1],
            cuad_mar_man_min=weekdays["cuad_mar"][0],
            cuad_mar_tar_min=weekdays["cuad_mar"][1],
            cuad_mie_man_min=weekdays["cuad_mie"][0],
            cuad_mie_tar_min=weekdays["cuad_mie"][1],
            cuad_jue_man_min=weekdays["cuad_jue"][0],
            cuad_jue_tar_min=weekdays["cuad_jue"][1],
            cuad_vie_man_min=weekdays["cuad_vie"][0],
            cuad_vie_tar_min=weekdays["cuad_vie"][1],
            cuad_sab_man_min=self.cuad_inputs["cuad_sab"]["man"].minutes(),
            cuad_sab_tar_min=self.cuad_inputs["cuad_sab"]["tar"].minutes(),
            cuad_dom_man_min=self.cuad_inputs["cuad_dom"]["man"].minutes(),
            cuad_dom_tar_min=self.cuad_inputs["cuad_dom"]["tar"].minutes(),
            cuadrante_uniforme=self.uniform_radio.isChecked(),
            trabaja_finde=self.trabaja_finde_check.isChecked(),
        )
