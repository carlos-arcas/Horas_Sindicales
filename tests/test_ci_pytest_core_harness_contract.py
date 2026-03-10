from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_ci_core_no_ui_desactiva_autoload_y_reinyecta_plugins_necesarios() -> None:
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(
        encoding="utf-8", errors="ignore"
    )

    assert 'PYTEST_DISABLE_PLUGIN_AUTOLOAD: "1"' in workflow
    assert 'PYTEST_CORE_SIN_QT: "1"' in workflow
    assert 'pytest -q -p pytest_cov -p no:pytestqt -p no:pytestqt.plugin -m "not ui" tests/test_no_secrets_content_scan.py' in workflow
    assert 'PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTEST_CORE_SIN_QT=1 pytest -q -p pytest_cov -p no:pytestqt -p no:pytestqt.plugin -m "not ui" ${COVERAGE_TARGETS}' in workflow
