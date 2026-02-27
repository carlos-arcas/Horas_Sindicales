from __future__ import annotations

from dataclasses import dataclass

from app.infrastructure.health_probes import DefaultConnectivityProbe, SQLiteLocalDbProbe


class _SocketOk:
    def __init__(self) -> None:
        self.calls = 0

    def create_connection(self, *_args, **_kwargs):
        self.calls += 1

        class _Conn:
            def close(self):
                return None

        return _Conn()


class _SocketFailApi:
    def __init__(self) -> None:
        self.calls = 0

    def create_connection(self, endpoint, **_kwargs):
        self.calls += 1
        if endpoint[0] == "sheets.googleapis.com":
            raise OSError("api down")

        class _Conn:
            def close(self):
                return None

        return _Conn()


def test_connectivity_probe_ok(monkeypatch) -> None:
    fake = _SocketOk()
    monkeypatch.setattr("app.infrastructure.health_probes.socket", fake)
    monkeypatch.setattr("app.infrastructure.health_probes.time.perf_counter", lambda: 10.0)
    ok_internet, ok_api, latency, msg = DefaultConnectivityProbe().check()
    assert (ok_internet, ok_api) == (True, True)
    assert latency == 0.0
    assert "Latencia aproximada API" in msg


def test_connectivity_probe_sin_api(monkeypatch) -> None:
    fake = _SocketFailApi()
    monkeypatch.setattr("app.infrastructure.health_probes.socket", fake)
    ok_internet, ok_api, latency, msg = DefaultConnectivityProbe().check()
    assert (ok_internet, ok_api, latency) == (True, False, None)
    assert "Latencia no disponible" in msg


@dataclass
class _CursorFake:
    responses: list[object]
    fail: bool = False
    index: int = 0

    def execute(self, _sql: str):
        if self.fail:
            raise RuntimeError("db rota")

    def fetchone(self):
        value = self.responses[self.index]
        self.index += 1
        return value


class _ConnectionFake:
    def __init__(self, cursor: _CursorFake) -> None:
        self._cursor = cursor
        self.closed = False

    def cursor(self):
        return self._cursor

    def close(self):
        self.closed = True


class _ConnectionSinClose:
    def cursor(self):
        return _CursorFake([1, {"total": 0}, {"total": 0}])


def test_sqlite_probe_happy_path() -> None:
    cursor = _CursorFake([1, {"total": 4}, {"total": 0}])
    conn = _ConnectionFake(cursor)
    result = SQLiteLocalDbProbe(lambda: conn, migrations_total=3).check()
    assert result["local_db"][0] is True
    assert result["migrations"][0] is True
    assert result["ghost_pending"][0] is True
    assert conn.closed is True


def test_sqlite_probe_migrations_y_ghost_pendiente() -> None:
    cursor = _CursorFake([1, {"total": 1}, {"total": 2}])
    conn = _ConnectionFake(cursor)
    result = SQLiteLocalDbProbe(lambda: conn, migrations_total=3).check()
    assert result["migrations"][0] is False
    assert "Hay migraciones pendientes" in result["migrations"][1]
    assert result["ghost_pending"][0] is False


def test_sqlite_probe_rama_excepcion() -> None:
    conn = _ConnectionFake(_CursorFake([], fail=True))
    result = SQLiteLocalDbProbe(lambda: conn).check()
    assert result["local_db"][0] is False
    assert "no accesible" in result["local_db"][1].lower()
    assert conn.closed is True


def test_sqlite_probe_sin_close_no_explota() -> None:
    result = SQLiteLocalDbProbe(lambda: _ConnectionSinClose()).check()
    assert result["local_db"][0] is True
