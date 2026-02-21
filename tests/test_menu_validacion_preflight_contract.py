from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_menu_validacion_preflight_contract() -> None:
    menu = ROOT / "menu_validacion.bat"
    content = menu.read_text(encoding="utf-8").lower()

    assert 'if not exist "%root_dir%ejecutar_tests.bat"' in content
    assert 'if not exist "%root_dir%quality_gate.bat"' in content
    assert 'if not exist "%log_dir%" mkdir "%log_dir%"' in content
    assert "menu_tests_env.txt" in content
    assert "2>>\"%summary_file%\"" in content
