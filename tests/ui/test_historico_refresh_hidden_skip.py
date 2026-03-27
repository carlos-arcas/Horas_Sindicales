from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

from app.ui.vistas.main_window import data_refresh


def test_refresh_historico_omite_consulta_si_pestana_historico_no_esta_visible() -> None:
    controller = SimpleNamespace(refresh_historico=Mock())
    window = SimpleNamespace(
        historico_table=object(),
        historico_model=object(),
        main_tabs=SimpleNamespace(currentIndex=Mock(return_value=0)),
        _solicitudes_controller=controller,
    )

    data_refresh.refresh_historico(window, force=False)

    controller.refresh_historico.assert_not_called()
