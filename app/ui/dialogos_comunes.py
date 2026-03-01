from __future__ import annotations

try:
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QDialog, QMessageBox, QPlainTextEdit, QPushButton, QVBoxLayout
except Exception:  # pragma: no cover - permite importar en CI sin Qt
    Qt = object
    QDialog = QMessageBox = QPlainTextEdit = QPushButton = QVBoxLayout = object

from app.ui.patterns import apply_modal_behavior


def show_message_with_details(
    parent,
    title: str,
    message: str,
    details: str | None,
    icon,
    action_buttons: tuple[tuple[str, object], ...] = (),
) -> None:
    dialog = QMessageBox(parent)
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
        show_details_dialog(parent, title, details)


def show_details_dialog(parent, title: str, details: str) -> None:
    dialog = QDialog(parent)
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
