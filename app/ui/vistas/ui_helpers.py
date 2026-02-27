from __future__ import annotations

from pathlib import Path


def abrir_archivo_local(path: Path) -> None:
    from PySide6.QtCore import QUrl
    from PySide6.QtGui import QDesktopServices

    QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))


def abrir_carpeta_contenedora(path: Path) -> None:
    abrir_archivo_local(path.parent)
