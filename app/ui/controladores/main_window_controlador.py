from __future__ import annotations

from app.ui.estado.estado_main_window import EstadoMainWindow


class MainWindowControlador:
    """Orquesta acciones principales de MainWindow sin lógica de negocio."""

    def __init__(self, sync_use_case, estado: EstadoMainWindow) -> None:
        self._sync_use_case = sync_use_case
        self._estado = estado

    @property
    def estado(self) -> EstadoMainWindow:
        return self._estado

    def on_sync_clicked(self):
        if self._estado.sync_en_progreso:
            return None
        self._estado.sync_en_progreso = True
        try:
            return self._sync_use_case.sync_bidirectional()
        finally:
            self._estado.sync_en_progreso = False
