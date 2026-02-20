from pathlib import Path
from fnmatch import fnmatch


EXCLUDED_DIRS = {
    ".git",
    ".venv",
    "dist",
    "build",
    "logs",
}

PROHIBITED_PATTERNS = [
    "credentials*.json",
    "token*.json",
    ".env",
    "*.db",
    "client_secret*.json",
]


def _is_excluded(path: Path) -> bool:
    return any(part in EXCLUDED_DIRS for part in path.parts)


def _find_prohibited_files(repo_root: Path) -> list[str]:
    found: list[str] = []

    for path in repo_root.rglob("*"):
        if not path.is_file() or _is_excluded(path):
            continue

        if any(fnmatch(path.name, pattern) for pattern in PROHIBITED_PATTERNS):
            found.append(path.relative_to(repo_root).as_posix())

    return sorted(found)


def test_no_prohibited_files_in_working_tree() -> None:
    repo_root = Path.cwd()
    blocked_files = _find_prohibited_files(repo_root)

    assert not blocked_files, (
        "Se han detectado ficheros prohibidos en el repositorio: "
        + ", ".join(blocked_files)
    )
