from pathlib import Path


def test_main_window_builder_uses_tabs_instead_of_sidebar() -> None:
    source = Path("app/ui/vistas/builders/main_window_builders.py").read_text(encoding="utf-8")

    assert "QTabWidget" in source
    assert 'addTab(operativa_tab, "Solicitudes")' in source
    assert 'addTab(historico_tab, "Histórico")' in source
    assert 'addTab(config_tab, "Configuración")' in source

    assert "Navegación" not in source
    assert 'setObjectName("sidebar")' not in source
