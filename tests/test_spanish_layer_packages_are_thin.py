from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BRIDGE_PACKAGES = ("dominio", "aplicacion", "infraestructura", "presentacion")


def test_spanish_bridge_packages_are_thin() -> None:
    for package in BRIDGE_PACKAGES:
        init_file = PROJECT_ROOT / package / "__init__.py"
        assert init_file.exists(), f"Debe existir {init_file.as_posix()}"

        content = init_file.read_text(encoding="utf-8")
        lines = content.splitlines()

        assert len(lines) <= 50, f"{init_file.as_posix()} excede 50 líneas"
        assert "def " not in content, f"{init_file.as_posix()} no puede declarar funciones"
        assert "class " not in content, f"{init_file.as_posix()} no puede declarar clases"

        allowed_prefixes = (
            '"""',
            "'''",
            "from ",
            "import ",
            "#",
        )
        for raw_line in lines:
            line = raw_line.strip()
            if not line:
                continue
            assert line.startswith(allowed_prefixes), (
                f"{init_file.as_posix()} debe contener solo comentarios/docstring/imports. "
                f"Línea inválida: {line!r}"
            )
