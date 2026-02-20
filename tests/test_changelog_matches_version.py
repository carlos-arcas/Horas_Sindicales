from pathlib import Path
import re


HEADER_PATTERN = r"^## \[(?P<version>\d+\.\d+\.\d+)\] - (?P<date>\d{4}-\d{2}-\d{2})$"


def test_changelog_has_entry_for_version_with_valid_format_and_content() -> None:
    root = Path(__file__).resolve().parents[1]
    version_path = root / "VERSION"
    changelog_path = root / "CHANGELOG.md"

    assert version_path.exists(), "Falta VERSION; créalo antes de validar el changelog."
    assert changelog_path.exists(), "Falta CHANGELOG.md en la raíz del repositorio."

    version = version_path.read_text(encoding="utf-8").strip()
    changelog_lines = changelog_path.read_text(encoding="utf-8").splitlines()

    expected_header = re.compile(
        rf"^## \[{re.escape(version)}\] - (\d{{4}}-\d{{2}}-\d{{2}})$"
    )

    matching_header_index = None
    for idx, line in enumerate(changelog_lines):
        if expected_header.match(line.strip()):
            matching_header_index = idx
            break

    assert matching_header_index is not None, (
        "No existe una cabecera exacta para la versión de VERSION en CHANGELOG.md. "
        f"Añade una línea con este formato: ## [{version}] - YYYY-MM-DD"
    )

    # Validación general del formato de cabeceras versionadas del changelog.
    for line in changelog_lines:
        candidate = line.strip()
        if candidate.startswith("## [") and candidate != "## [Unreleased]":
            assert re.fullmatch(HEADER_PATTERN, candidate), (
                "Formato inválido en cabecera versionada de CHANGELOG.md. "
                "Usa: ## [X.Y.Z] - YYYY-MM-DD"
            )

    # La sección no debe estar vacía: debe tener al menos un subtítulo ### o un bullet.
    section_lines = []
    for line in changelog_lines[matching_header_index + 1 :]:
        if line.strip().startswith("## "):
            break
        section_lines.append(line.strip())

    has_content = any(line.startswith("### ") or line.startswith("-") for line in section_lines)
    assert has_content, (
        f"La sección ## [{version}] no puede estar vacía. "
        "Incluye al menos un subtítulo '###' o un bullet '-'."
    )
