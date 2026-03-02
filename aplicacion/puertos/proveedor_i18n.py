from __future__ import annotations

from typing import Protocol


class ProveedorI18N(Protocol):
    def t(self, key: str, fallback: str | None = None, **vars: object) -> str:
        ...


IProveedorI18N = ProveedorI18N
