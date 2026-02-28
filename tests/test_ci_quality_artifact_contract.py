from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_ci_uploada_artifact_quality_gate() -> None:
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8", errors="ignore"
    )

    assert "actions/upload-artifact@v4" in workflow
    assert "quality-gate-report-py${{ matrix.python-version }}" in workflow
    assert "logs/quality_report.md" in workflow
    assert "logs/quality_report.json" in workflow


def test_readme_documenta_quality_gate_y_modo_degradado() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8", errors="ignore")
    readme_lower = readme.lower()

    assert "## quality gate" in readme_lower
    assert "quality_gate.bat" in readme
    assert "python scripts/quality_gate.py" in readme
    assert "--allow-missing-pytest-cov" in readme
    assert "estado global" in readme_lower and "fail" in readme_lower
