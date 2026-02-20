from pathlib import Path
import re


def test_version_file_exists_and_is_valid_semver() -> None:
    version_path = Path(__file__).resolve().parents[1] / "VERSION"
    assert version_path.exists(), (
        "Falta el archivo VERSION en la raíz del repositorio. "
        "Crea VERSION con formato MAJOR.MINOR.PATCH, por ejemplo 0.1.0."
    )

    version = version_path.read_text(encoding="utf-8").strip()
    assert re.fullmatch(r"\d+\.\d+\.\d+", version), (
        "El archivo VERSION es inválido. "
        "Debe contener una sola línea con formato MAJOR.MINOR.PATCH sin prefijo 'v'."
    )
