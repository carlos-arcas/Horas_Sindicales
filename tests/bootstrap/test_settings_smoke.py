from __future__ import annotations

from pathlib import Path

from app.bootstrap import settings


def test_resolve_log_dir_uses_env_path(monkeypatch, tmp_path) -> None:
    env_dir = tmp_path / "env_logs"
    monkeypatch.setenv("HORAS_LOG_DIR", str(env_dir))

    resolved = settings.resolve_log_dir()

    assert resolved == env_dir
    assert resolved.exists()


def test_resolve_log_dir_falls_back_to_project_root(monkeypatch, tmp_path) -> None:
    project_root = tmp_path / "project"
    monkeypatch.delenv("HORAS_LOG_DIR", raising=False)
    monkeypatch.setattr(settings, "project_root", lambda: project_root)
    monkeypatch.setattr(settings.tempfile, "gettempdir", lambda: str(tmp_path / "tmpbase"))

    original_mkdir = Path.mkdir

    def failing_candidate_mkdir(self: Path, parents: bool = False, exist_ok: bool = False):
        if self in {project_root / "logs", tmp_path / "tmpbase" / "HorasSindicales" / "logs"}:
            raise OSError("cannot create candidate")
        return original_mkdir(self, parents=parents, exist_ok=exist_ok)

    monkeypatch.setattr(Path, "mkdir", failing_candidate_mkdir)

    resolved = settings.resolve_log_dir()

    assert resolved == project_root
    assert resolved.exists()
