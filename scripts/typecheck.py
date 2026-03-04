from __future__ import annotations

import subprocess
import sys


def main() -> int:
    return subprocess.call(
        [
            sys.executable,
            "-m",
            "mypy",
            "--config-file",
            ".config/mypy.ini",
        ]
    )


if __name__ == "__main__":
    raise SystemExit(main())
