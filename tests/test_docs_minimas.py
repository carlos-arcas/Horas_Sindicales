from __future__ import annotations

from pathlib import Path


DOCS_REQUERIDAS = {
    "README.md": Path("README.md"),
    "Arquitectura": Path("docs/arquitectura.md"),
    "Decisiones técnicas": Path("docs/decisiones_tecnicas.md"),
    "Guía de pruebas": Path("docs/guia_pruebas.md"),
    "Guía de logging": Path("docs/guia_logging.md"),
    "Definición producto final": Path("docs/definicion_producto_final.md"),
}


def _leer_doc(repo_root: Path, doc_path: Path) -> str:
    absolute = repo_root / doc_path
    assert absolute.exists(), (
        f"Falta documentación obligatoria: '{doc_path.as_posix()}'. "
        "Créala o restáurala para cumplir el estándar mínimo."
    )
    return absolute.read_text(encoding="utf-8")


def test_docs_minimas_existen() -> None:
    repo_root = Path(__file__).resolve().parents[1]

    faltantes: list[str] = []
    for nombre, path in DOCS_REQUERIDAS.items():
        if not (repo_root / path).exists():
            faltantes.append(f"- {nombre}: {path.as_posix()}")

    assert not faltantes, (
        "Faltan documentos mínimos obligatorios:\n"
        + "\n".join(faltantes)
        + "\nAñade los archivos indicados en /docs y README.md en raíz."
    )


def test_docs_minimas_tienen_h1_y_contenido_minimo() -> None:
    repo_root = Path(__file__).resolve().parents[1]

    for nombre, path in DOCS_REQUERIDAS.items():
        contenido = _leer_doc(repo_root, path)
        lineas = contenido.splitlines()

        assert any(line.startswith("# ") for line in lineas), (
            f"El documento '{path.as_posix()}' ({nombre}) debe incluir un título H1 ('# ...')."
        )

        tiene_largo_minimo = len(lineas) > 30 or len(contenido) > 500
        assert tiene_largo_minimo, (
            f"El documento '{path.as_posix()}' parece un stub vacío "
            f"({len(lineas)} líneas, {len(contenido)} caracteres). "
            "Amplíalo con contenido útil y verificable."
        )


def test_arquitectura_define_cadena_dependencias() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    contenido = _leer_doc(repo_root, Path("docs/arquitectura.md")).lower()

    assert "dominio <- aplicacion <-" in contenido, (
        "'docs/arquitectura.md' debe documentar explícitamente la cadena "
        "de dependencias por capas (ej.: 'dominio <- aplicacion <- ...')."
    )


def test_guia_pruebas_menciona_pytest_y_cobertura() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    contenido = _leer_doc(repo_root, Path("docs/guia_pruebas.md")).lower()

    assert "pytest" in contenido, "'docs/guia_pruebas.md' debe mencionar 'pytest'."
    assert "--cov" in contenido, "'docs/guia_pruebas.md' debe mencionar el uso de '--cov'."


def test_guia_logging_menciona_archivos_clave() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    contenido = _leer_doc(repo_root, Path("docs/guia_logging.md")).lower()

    assert "seguimiento.log" in contenido, "'docs/guia_logging.md' debe mencionar 'seguimiento.log'."
    assert "crashes.log" in contenido, "'docs/guia_logging.md' debe mencionar 'crashes.log'."
