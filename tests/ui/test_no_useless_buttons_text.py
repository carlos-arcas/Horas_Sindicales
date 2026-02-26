from pathlib import Path


def test_builder_solicitudes_sin_botones_reduntantes() -> None:
    builder_source = Path("app/ui/vistas/builders/main_window_builders.py").read_text(encoding="utf-8")

    assert "Nueva solicitud" not in builder_source
    assert "Añadir a pendientes" not in builder_source
