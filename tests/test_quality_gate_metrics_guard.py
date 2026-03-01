from __future__ import annotations

import ast
import importlib.util
import os
from pathlib import Path


def _metrics_test_path() -> Path:
    root = Path(__file__).resolve().parents[1]
    return root / "tests" / "test_quality_gate_metrics.py"


def test_quality_gate_metrics_no_importa_modulos_app() -> None:
    """Guard: el test de métricas debe operar por lectura de archivos, sin importar app.*."""

    tree = ast.parse(_metrics_test_path().read_text(encoding="utf-8"))
    forbidden_imports = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "app" or alias.name.startswith("app."):
                    forbidden_imports.append(alias.name)
        if isinstance(node, ast.ImportFrom) and node.module:
            if node.module == "app" or node.module.startswith("app."):
                forbidden_imports.append(node.module)

    assert not forbidden_imports, (
        "tests/test_quality_gate_metrics.py no debe importar módulos de app para evitar "
        f"side effects de Qt/UI. Imports detectados: {sorted(set(forbidden_imports))}"
    )


def test_radon_obligatorio_en_ci_para_quality_gate() -> None:
    """Guard mínimo: en CI, radon debe existir para evitar SKIP en métricas."""

    if os.getenv("CI", "").lower() not in {"1", "true", "yes"}:
        return

    assert importlib.util.find_spec("radon") is not None, (
        "En CI debe instalarse radon (requirements-dev.txt) para que el gate de "
        "métricas LOC/CC sea determinista y no quede SKIPPED."
    )
