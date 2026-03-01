from pathlib import Path

EXCLUDED_DIRS = {
    ".git",
    ".venv",
    "build",
    "dist",
    "logs",
    "tests",
    "__pycache__",
}
MAX_FILE_SIZE_BYTES = 2 * 1024 * 1024
CONTENT_PATTERNS: tuple[tuple[str, str], ...] = (
    ("BEGIN PRIVATE KEY", "begin private key"),
    ('"private_key"', '"private_key"'),
    ('"client_secret"', '"client_secret"'),
    ("AIza", "aiza"),
    ("ya29.", "ya29."),
    ("authorization: bearer", "authorization: bearer"),
)


def _is_excluded(path: Path) -> bool:
    return any(part in EXCLUDED_DIRS for part in path.parts)


def _find_secret_content(repo_root: Path) -> list[str]:
    detections: list[str] = []

    for path in repo_root.rglob("*"):
        if not path.is_file() or _is_excluded(path):
            continue

        if path.stat().st_size > MAX_FILE_SIZE_BYTES:
            continue

        content = path.read_text(encoding="utf-8", errors="ignore").lower()

        for pattern_label, pattern_lower in CONTENT_PATTERNS:
            if pattern_lower in content:
                relative_path = path.relative_to(repo_root).as_posix()
                detections.append(f"{relative_path}: {pattern_label} (SECRETO DETECTADO)")

    return sorted(detections)


def test_no_secret_content_in_working_tree() -> None:
    detections = _find_secret_content(Path.cwd())

    assert not detections, (
        "Se detectó contenido sensible en el repositorio (sin exponer secretos): "
        + ", ".join(detections)
    )


def test_detects_dummy_private_key_content(tmp_path: Path) -> None:
    dummy_file = tmp_path / "dummy.json"
    dummy_file.write_text('{"private_key": "not-a-real-secret"}', encoding="utf-8")

    detections = _find_secret_content(tmp_path)

    assert len(detections) == 1
    assert "dummy.json" in detections[0]
    assert '"private_key"' in detections[0]
    assert "SECRETO DETECTADO" in detections[0]


def test_does_not_scan_excluded_directories(tmp_path: Path) -> None:
    excluded_file = tmp_path / ".git" / "secrets.txt"
    excluded_file.parent.mkdir(parents=True)
    excluded_file.write_text("authorization: bearer should be ignored", encoding="utf-8")

    detections = _find_secret_content(tmp_path)

    assert detections == []
