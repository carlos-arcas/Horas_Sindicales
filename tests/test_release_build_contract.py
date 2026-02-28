from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_release_build_contract() -> None:
    spec_path = ROOT / "packaging" / "HorasSindicales.spec"
    workflow_path = ROOT / ".github" / "workflows" / "release_build_windows.yml"
    version_path = ROOT / "VERSION"
    requirements_dev_path = ROOT / "requirements-dev.txt"

    assert spec_path.exists(), "Debe existir packaging/HorasSindicales.spec"
    assert workflow_path.exists(), "Debe existir .github/workflows/release_build_windows.yml"
    assert version_path.exists(), "Debe existir VERSION"
    assert requirements_dev_path.exists(), "Debe existir requirements-dev.txt"

    version = version_path.read_text(encoding="utf-8").strip()
    assert re.fullmatch(r"\d+\.\d+\.\d+", version), (
        "VERSION debe seguir MAJOR.MINOR.PATCH"
    )

    requirements_dev = requirements_dev_path.read_text(encoding="utf-8")
    assert re.search(r"^pyinstaller==\d+\.\d+\.\d+$", requirements_dev, re.MULTILINE), (
        "requirements-dev.txt debe incluir pyinstaller pinneado"
    )
