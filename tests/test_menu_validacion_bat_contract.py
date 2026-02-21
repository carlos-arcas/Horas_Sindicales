from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _branch(content: str, label: str) -> str:
    marker = f"\n{label}"
    start = content.index(marker) + 1
    next_label = content.find("\n:", start + 1)
    if next_label == -1:
        return content[start:]
    return content[start:next_label]


def test_menu_validacion_bat_contract() -> None:
    menu = ROOT / "menu_validacion.bat"

    assert menu.exists(), "Debe existir menu_validacion.bat en la raiz"

    content = menu.read_text(encoding="utf-8").lower()

    assert "%~dp0" in content, "menu_validacion.bat debe usar rutas relativas con %~dp0"
    assert "ejecutar_tests.bat" in content, "menu_validacion.bat debe delegar en ejecutar_tests.bat"
    assert "quality_gate.bat" in content, "menu_validacion.bat debe delegar en quality_gate.bat"
    assert "logs\\menu_ultima_ejecucion.txt" in content, (
        "menu_validacion.bat debe escribir logs\\menu_ultima_ejecucion.txt"
    )

    for option in ("1)", "2)", "3)", "0)"):
        assert option in content, f"menu_validacion.bat debe contener la opcion {option}"

    assert "powershell" not in content, "menu_validacion.bat no debe usar powershell"


def test_menu_validacion_controla_exit_en_menu() -> None:
    menu = ROOT / "menu_validacion.bat"
    content = menu.read_text(encoding="utf-8").lower()

    menu_branch = _branch(content, ":menu")
    assert "exit /b" not in menu_branch, "El flujo del menu no debe usar exit directo"
    assert "call :finalize_action" in content


def test_menu_validacion_logs_pre_post_y_streams() -> None:
    content = (ROOT / "menu_validacion.bat").read_text(encoding="utf-8").lower()

    assert "logs\\menu_tests_env.txt" in content
    assert "tests_stdout.txt" in content
    assert "tests_stderr.txt" in content
    assert 'call :write_menu_env "pre"' in content
    assert 'call :write_menu_env "post"' in content


def test_opcion_6_no_ejecuta_pytest() -> None:
    content = (ROOT / "menu_validacion.bat").read_text(encoding="utf-8")
    branch_6 = _branch(content, ":OPEN_LAST_COVERAGE_HTML")
    branch_6_lower = branch_6.lower()

    assert "pytest" not in branch_6_lower
    assert "coverage report" not in branch_6_lower
    assert "coverage html" not in branch_6_lower
    assert "call :safe_open" in branch_6_lower
