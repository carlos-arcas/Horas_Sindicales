from __future__ import annotations

from pathlib import Path
from typing import Any


def aplicar_tema(app: Any) -> None:
    qss_path = Path(__file__).with_name("tema.qss")
    app.setStyleSheet(qss_path.read_text(encoding="utf-8"))
