from __future__ import annotations

import pytest


django = pytest.importorskip("django", reason="Django no está instalado en este entorno")


def test_smoke_django_importado() -> None:
    assert django is not None
