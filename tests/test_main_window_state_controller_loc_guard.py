from __future__ import annotations

from pathlib import Path


STATE_CONTROLLER_PATH = Path("app/ui/vistas/main_window/state_controller.py")
MAX_NON_EMPTY_LOC = 1117


def _count_non_empty_lines(path: Path) -> int:
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def test_state_controller_non_empty_loc_guard() -> None:
    current_loc = _count_non_empty_lines(STATE_CONTROLLER_PATH)

    assert current_loc <= MAX_NON_EMPTY_LOC, (
        "Regresión detectada: app/ui/vistas/main_window/state_controller.py "
        f"tiene {current_loc} líneas no vacías y el máximo permitido es "
        f"{MAX_NON_EMPTY_LOC}. Extrae responsabilidades antes de agregar LOC."
    )
