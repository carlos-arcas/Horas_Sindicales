#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FEATURES_SOURCE = ROOT / "docs" / "features.json"
FEATURES_MD = ROOT / "docs" / "features.md"
FEATURES_PENDING_MD = ROOT / "docs" / "features_pendientes.md"
VALID_STATES = {"DONE", "TODO", "WIP", "BLOCKED"}
VALID_TYPES = {"LOGICA", "UI", "SEGURIDAD", "INFRA"}


def _load_features() -> list[dict[str, object]]:
    data = json.loads(FEATURES_SOURCE.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise SystemExit("docs/features.json debe ser una lista de features")
    for item in data:
        if not isinstance(item, dict):
            raise SystemExit("Cada feature debe ser un objeto JSON")
        missing = {"id", "nombre", "estado", "tipo", "tests"} - set(item)
        if missing:
            raise SystemExit(f"Feature incompleta ({item}): faltan {sorted(missing)}")
        if item["estado"] not in VALID_STATES:
            raise SystemExit(
                f"Estado inválido en feature {item['id']}: {item['estado']}"
            )
        if item["tipo"] not in VALID_TYPES:
            raise SystemExit(f"Tipo inválido en feature {item['id']}: {item['tipo']}")
        if not isinstance(item["tests"], list):
            raise SystemExit(f"tests debe ser lista en feature {item['id']}")
    return data


def _build_md(features: list[dict[str, object]]) -> str:
    rows = [
        "# Inventario de features",
        "",
        "| ID | Nombre | Estado | Tipo | Tests | Notas |",
        "|---|---|---|---|---|---|",
    ]
    for feature in features:
        tests = "<br>".join(str(test) for test in feature["tests"]) or "-"
        notas = str(feature.get("notas", "-")).replace("|", "\\|")
        rows.append(
            f"| {feature['id']} | {feature['nombre']} | {feature['estado']} | {feature['tipo']} | {tests} | {notas} |"
        )
    return "\n".join(rows) + "\n"


def _build_pending_md(features: list[dict[str, object]]) -> str:
    pendientes = [f for f in features if f["estado"] != "DONE"]
    rows = ["# Features pendientes", ""]
    if not pendientes:
        rows.append("- No hay pendientes.")
        return "\n".join(rows) + "\n"

    for feature in pendientes:
        rows.extend(
            [
                f"## {feature['id']} - {feature['nombre']}",
                f"- Estado: **{feature['estado']}**",
                f"- Tipo: `{feature['tipo']}`",
                "- Tests:",
            ]
        )
        for test in feature["tests"]:
            rows.append(f"  - `{test}`")
        notas = feature.get("notas")
        if notas:
            rows.append(f"- Notas: {notas}")
        rows.append("")
    return "\n".join(rows)


def main() -> int:
    features = _load_features()
    FEATURES_MD.write_text(_build_md(features), encoding="utf-8")
    FEATURES_PENDING_MD.write_text(_build_pending_md(features), encoding="utf-8")
    print("features docs regenerados")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
