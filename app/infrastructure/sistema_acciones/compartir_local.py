from __future__ import annotations

from pathlib import Path
from urllib.parse import quote


def abrir_carpeta(ruta: Path) -> str:
    return str(ruta)


def construir_mailto(destinatario: str, asunto: str, cuerpo: str) -> str:
    return f"mailto:{destinatario}?subject={quote(asunto)}&body={quote(cuerpo)}"
