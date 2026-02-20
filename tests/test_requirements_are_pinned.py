from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PINNED_PATTERN = re.compile(r"^[A-Za-z0-9_.\-\[\],]+==[A-Za-z0-9_.\-+!]+(?:\s*;\s*.+)?$")
DISALLOWED_OPERATORS = (">=", "<=", "<", ">")


def _validate_requirements_file(path: Path) -> list[str]:
    errors: list[str] = []
    for lineno, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()

        if not line or line.startswith("#"):
            continue

        if any(operator in line for operator in DISALLOWED_OPERATORS):
            errors.append(
                f"{path.name}:{lineno} contiene operador no permitido ({line!r}). "
                "Usa versiones pinneadas con ==."
            )
            continue

        if line.startswith("-r ") or line.startswith("--"):
            continue

        if not PINNED_PATTERN.match(line):
            errors.append(
                f"{path.name}:{lineno} tiene formato no permitido ({line!r}). "
                "Solo se admite package==version, '-r ...' o flags '--...'."
            )

    return errors


def test_requirements_txt_y_dev_txt_estan_pinneados() -> None:
    target_files = [ROOT / "requirements.txt", ROOT / "requirements-dev.txt"]
    all_errors: list[str] = []

    for req_file in target_files:
        assert req_file.exists(), f"No existe el archivo requerido: {req_file}"
        all_errors.extend(_validate_requirements_file(req_file))

    assert not all_errors, "\n".join(all_errors)
