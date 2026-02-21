from __future__ import annotations

from PySide6.QtWidgets import QMessageBox, QWidget


def confirmar(parent: QWidget | None, titulo: str, mensaje: str) -> bool:
    return QMessageBox.question(parent, titulo, mensaje) == QMessageBox.Yes


def informar(parent: QWidget | None, titulo: str, mensaje: str) -> None:
    QMessageBox.information(parent, titulo, mensaje)


def error(parent: QWidget | None, titulo: str, mensaje: str) -> None:
    QMessageBox.critical(parent, titulo, mensaje)
