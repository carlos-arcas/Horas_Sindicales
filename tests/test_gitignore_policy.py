from pathlib import Path


REQUIRED_PATTERNS = [
    "*.db",
    "credentials*.json",
    ".env",
    "__pycache__/",
]

VENV_PATTERNS = {".venv/", ".venv"}


def test_gitignore_exists() -> None:
    gitignore_path = Path(".gitignore")
    assert gitignore_path.exists(), "Falta el fichero .gitignore en la raíz del repositorio."


def test_gitignore_contains_critical_patterns() -> None:
    gitignore_path = Path(".gitignore")
    content = gitignore_path.read_text(encoding="utf-8")

    missing = [pattern for pattern in REQUIRED_PATTERNS if pattern not in content]
    assert not missing, (
        "Faltan patrones críticos en .gitignore: " + ", ".join(missing)
    )

    has_venv = any(pattern in content for pattern in VENV_PATTERNS)
    assert has_venv, "Falta patrón de entorno virtual (.venv o .venv/) en .gitignore."
