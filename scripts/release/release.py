#!/usr/bin/env python3
from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VERSION_FILE = ROOT / "app" / "__init__.py"
CHANGELOG_FILE = ROOT / "CHANGELOG.md"
SEMVER_PATTERN = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")


def run(command: list[str]) -> None:
    result = subprocess.run(command, cwd=ROOT)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def ensure_git_clean() -> None:
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    if result.stdout.strip():
        raise SystemExit(
            "Working tree is not clean. Commit or stash changes before running release-check."
        )


def read_version() -> str:
    content = VERSION_FILE.read_text(encoding="utf-8")
    match = re.search(r'__version__\s*=\s*"([^"]+)"', content)
    if not match:
        raise SystemExit(f"Could not find __version__ in {VERSION_FILE}")
    version = match.group(1)
    if not SEMVER_PATTERN.match(version):
        raise SystemExit(f"Invalid SemVer version: {version}")
    return version


def ensure_changelog_version(version: str) -> None:
    changelog = CHANGELOG_FILE.read_text(encoding="utf-8")
    if f"## [{version}]" not in changelog:
        raise SystemExit(
            f"CHANGELOG.md must include a section for version [{version}] before release."
        )


def main() -> None:
    print("==> Checking git status")
    ensure_git_clean()

    print("==> Reading and validating version")
    version = read_version()
    print(f"Detected version: {version}")

    print("==> Verifying changelog entry")
    ensure_changelog_version(version)

    print("\nRelease checks passed.")
    print("Next steps:")
    print(f"1) git tag v{version}")
    print("2) git push --tags")
    print(f"3) Create GitHub Release for v{version} and paste CHANGELOG notes")


if __name__ == "__main__":
    main()
