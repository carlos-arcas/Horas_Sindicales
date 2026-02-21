from __future__ import annotations

import builtins
import importlib

import pytest


def test_metrics_test_skips_when_radon_is_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    module = importlib.import_module("tests.test_quality_gate_metrics")

    real_import = builtins.__import__

    def fake_import(name: str, *args, **kwargs):
        if name == "radon" or name.startswith("radon."):
            raise ImportError("simulated missing radon")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    with pytest.raises(pytest.skip.Exception):
        module.test_quality_gate_size_and_complexity()
