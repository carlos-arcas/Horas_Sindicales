"""Parámetros del quality gate para tamaño y complejidad."""

MAX_LOC_POR_ARCHIVO = 900
MAX_CC_POR_FUNCION = 20

RUTAS_EXCLUIDAS = {
    ".venv",
    ".git",
    "dist",
    "build",
    "logs",
    "tests",
    "migrations",
    "__pycache__",
}

EXCEPCIONES_LOC = {
    "app/application/use_cases/sync_sheets/use_case.py": 1694,
    "app/ui/vistas/main_window_vista.py": 3010,
}

EXCEPCIONES_CC = {
    "app/application/use_cases/sync_sheets/use_case.py:SheetsSyncUseCase._create_conflict": 35,
    "app/application/use_cases/sync_sheets/use_case.py:SheetsSyncUseCase._apply_pull_updates": 35,
    "app/application/use_cases/sync_sheets/use_case.py:SheetsSyncUseCase._run_push": 28,
    "app/application/use_cases/sync_sheets/use_case.py:SheetsSyncUseCase._normalize_row_to_entity": 25,
    "app/ui/vistas/main_window_vista.py:MainWindowVista._on_sync_error": 34,
    "app/ui/vistas/main_window_vista.py:MainWindowVista.refresh_all": 24,
}
