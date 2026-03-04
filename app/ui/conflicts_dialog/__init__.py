from __future__ import annotations

__all__ = ["ConflictsDialog"]


def __getattr__(name: str):
    if name == "ConflictsDialog":
        from .dialogo_qt import ConflictsDialog

        return ConflictsDialog
    raise AttributeError(name)
