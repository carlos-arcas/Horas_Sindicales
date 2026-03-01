from __future__ import annotations

from typing import Any


def is_qt_valid(obj: Any) -> bool:
    if obj is None:
        return False
    try:
        from shiboken6 import isValid as shiboken_is_valid
    except ImportError:
        pass
    else:
        try:
            return bool(shiboken_is_valid(obj))
        except RuntimeError:
            return False
    try:
        bool(obj)
        return True
    except RuntimeError:
        return False


def safe_call(obj: Any, method_name: str, *args: Any) -> None:
    if not is_qt_valid(obj):
        return
    try:
        getattr(obj, method_name)(*args)
    except RuntimeError:
        return
