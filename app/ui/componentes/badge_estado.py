from __future__ import annotations

from PySide6.QtWidgets import QLabel


class BadgeEstado(QLabel):
    ESTILOS = {
        "Pendiente": ("#FFF4DD", "#8A5B00"),
        "Confirmada": ("#EAF7EE", "#1F6D3D"),
        "Enviada": ("#EAF0FF", "#1D4AA6"),
    }

    def set_estado(self, estado: str) -> None:
        bg, fg = self.ESTILOS.get(estado, ("#ECEFF5", "#334155"))
        self.setText(estado)
        self.setStyleSheet(f"background:{bg};color:{fg};border-radius:8px;padding:2px 8px;")
