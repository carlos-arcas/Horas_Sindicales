from __future__ import annotations

from app.entrypoints import main as main_entry


def test_main_flush_handlers_en_finally(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(main_entry, "resolve_log_dir", lambda: tmp_path)
    monkeypatch.setattr(main_entry, "init_boot_diagnostics", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(main_entry, "configure_logging", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(main_entry, "run_ui", lambda: 0)

    flush_calls = {"count": 0}

    def _flush() -> None:
        flush_calls["count"] += 1

    monkeypatch.setattr(main_entry, "flush_logging_handlers", _flush)

    resultado = main_entry.main([])

    assert resultado == 0
    assert flush_calls["count"] == 1


def test_main_flush_handlers_ante_excepcion(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(main_entry, "resolve_log_dir", lambda: tmp_path)
    monkeypatch.setattr(main_entry, "init_boot_diagnostics", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(main_entry, "configure_logging", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(main_entry, "run_ui", lambda: (_ for _ in ()).throw(RuntimeError("fallo")))

    flush_calls = {"count": 0}

    def _flush() -> None:
        flush_calls["count"] += 1

    monkeypatch.setattr(main_entry, "flush_logging_handlers", _flush)

    try:
        main_entry.main([])
    except RuntimeError:
        pass

    assert flush_calls["count"] == 1
