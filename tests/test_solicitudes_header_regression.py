from pathlib import Path


def test_solicitudes_step_header_strings_removed() -> None:
    builder_path = Path(__file__).resolve().parents[1] / "app/ui/vistas/builders/main_window_builders.py"
    content = builder_path.read_text(encoding="utf-8")

    forbidden_tokens = (
        '"Alta de solicitud"',
        '"Completar datos"',
        '"Revisar pendientes",',
    )

    for token in forbidden_tokens:
        assert token not in content, f"No debe reaparecer la cabecera tipo wizard: {token}"
