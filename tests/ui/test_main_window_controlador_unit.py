from __future__ import annotations

from unittest.mock import Mock

from app.ui.controladores.main_window_controlador import MainWindowControlador
from app.ui.estado.estado_main_window import EstadoMainWindow


def test_on_sync_clicked_invoca_caso_de_uso_y_reinicia_estado() -> None:
    sync_use_case = Mock()
    sync_use_case.sync_bidirectional.return_value = {"ok": True}
    estado = EstadoMainWindow(sync_en_progreso=False)
    controlador = MainWindowControlador(sync_use_case=sync_use_case, estado=estado)

    resultado = controlador.on_sync_clicked()

    assert resultado == {"ok": True}
    sync_use_case.sync_bidirectional.assert_called_once_with()
    assert estado.sync_en_progreso is False


def test_on_sync_clicked_no_reentra_si_ya_esta_en_progreso() -> None:
    sync_use_case = Mock()
    estado = EstadoMainWindow(sync_en_progreso=True)
    controlador = MainWindowControlador(sync_use_case=sync_use_case, estado=estado)

    resultado = controlador.on_sync_clicked()

    assert resultado is None
    sync_use_case.sync_bidirectional.assert_not_called()
    assert estado.sync_en_progreso is True
