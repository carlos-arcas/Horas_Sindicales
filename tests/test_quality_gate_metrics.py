from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from radon.complexity import cc_visit
from radon.raw import analyze

from app.configuracion.calidad import (
    EXCEPCIONES_CC,
    EXCEPCIONES_LOC,
    MAX_CC_POR_FUNCION,
    MAX_LOC_POR_ARCHIVO,
    RUTAS_EXCLUIDAS,
)


@dataclass(frozen=True)
class LocViolation:
    file: str
    value: int
    limit: int

    @property
    def excess(self) -> int:
        return self.value - self.limit


@dataclass(frozen=True)
class CcViolation:
    identifier: str
    complexity: int
    limit: int

    @property
    def excess(self) -> int:
        return self.complexity - self.limit


def _iter_python_files() -> list[Path]:
    root = Path(__file__).resolve().parents[1]
    app_root = root / "app"
    files: list[Path] = []

    for path in app_root.rglob("*.py"):
        relative = path.relative_to(root)
        if any(part in RUTAS_EXCLUIDAS for part in relative.parts):
            continue
        files.append(path)

    return sorted(files)


def _format_loc_violations(violations: list[LocViolation]) -> str:
    top = sorted(violations, key=lambda item: item.value, reverse=True)[:10]
    lines = [
        "Top 10 archivos con LOC fuera de límite:",
        *[
            (
                f"  - {item.file}: {item.value} LOC "
                f"(límite {item.limit}, +{item.excess})"
            )
            for item in top
        ],
    ]
    return "\n".join(lines)


def _format_cc_violations(violations: list[CcViolation]) -> str:
    top = sorted(violations, key=lambda item: item.complexity, reverse=True)[:10]
    lines = [
        "Top 10 funciones/métodos con CC fuera de límite:",
        *[
            (
                f"  - {item.identifier}: CC {item.complexity} "
                f"(límite {item.limit}, +{item.excess})"
            )
            for item in top
        ],
    ]
    return "\n".join(lines)


def test_quality_gate_size_and_complexity() -> None:
    root = Path(__file__).resolve().parents[1]
    loc_violations: list[LocViolation] = []
    cc_violations: list[CcViolation] = []

    for path in _iter_python_files():
        source = path.read_text(encoding="utf-8")
        relative = path.relative_to(root).as_posix()

        loc_value = analyze(source).sloc
        loc_limit = EXCEPCIONES_LOC.get(relative, MAX_LOC_POR_ARCHIVO)
        if loc_value > loc_limit:
            loc_violations.append(LocViolation(file=relative, value=loc_value, limit=loc_limit))

        for block in cc_visit(source):
            if block.letter not in {"F", "M"}:
                continue

            if block.classname:
                identifier = f"{relative}:{block.classname}.{block.name}"
            else:
                identifier = f"{relative}:{block.name}"

            cc_limit = EXCEPCIONES_CC.get(identifier, MAX_CC_POR_FUNCION)
            if block.complexity > cc_limit:
                cc_violations.append(
                    CcViolation(identifier=identifier, complexity=block.complexity, limit=cc_limit)
                )

    report_sections: list[str] = []
    if loc_violations:
        report_sections.append(_format_loc_violations(loc_violations))
    if cc_violations:
        report_sections.append(_format_cc_violations(cc_violations))

    if report_sections:
        report_sections.append(
            "Sugerencia: refactorizar/extraer responsabilidades para reducir tamaño y complejidad."
        )

    assert not report_sections, "\n\n" + "\n\n".join(report_sections)
