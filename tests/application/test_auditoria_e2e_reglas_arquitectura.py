from __future__ import annotations

from pathlib import Path

import pytest

from app.application.auditoria_e2e.dto import EstadoCheck, SeveridadCheck
from app.application.auditoria_e2e.reglas import (
    _extraer_imports,
    _obtener_capa_modulo,
    _regla_domain_no_depende_infra,
    _regla_domain_no_depende_ui,
    _regla_ui_no_depende_infra,
    evaluar_reglas_arquitectura,
)


class FSBuilder:
    """Doble de filesystem en memoria para tests deterministas y sin IO real."""

    def __init__(self, archivos: dict[str, str]) -> None:
        self._archivos = {Path(ruta): contenido for ruta, contenido in archivos.items()}

    def listar_python(self, base: Path) -> list[Path]:
        prefijo = str(base)
        return sorted(path for path in self._archivos if str(path).startswith(prefijo) and path.suffix == ".py")

    def leer_texto(self, ruta: Path) -> str:
        return self._archivos[ruta]


@pytest.mark.parametrize(
    ("ruta", "esperada"),
    [
        ("/repo/app/ui/vista.py", "ui"),
        ("/repo/app/domain/entidad.py", "domain"),
        ("/repo/app/application/caso.py", "application"),
        ("/repo/app/infrastructure/db.py", "infrastructure"),
    ],
)
def test_obtener_capa_modulo_detecta_capas_validas(ruta: str, esperada: str) -> None:
    assert _obtener_capa_modulo(Path(ruta), Path("/repo")) == esperada


def test_obtener_capa_modulo_retorna_none_si_ruta_es_corta() -> None:
    assert _obtener_capa_modulo(Path("/repo/app.py"), Path("/repo")) is None


def test_obtener_capa_modulo_retorna_none_si_capa_no_reconocida() -> None:
    assert _obtener_capa_modulo(Path("/repo/app/shared/util.py"), Path("/repo")) is None


def test_extraer_imports_toma_imports_y_from_imports() -> None:
    tree = compile("import app.ui.x\nfrom app.infrastructure.repo import Repo", "<src>", "exec", flags=0x400)
    assert _extraer_imports(tree) == ["app.ui.x", "app.infrastructure.repo"]


def test_extraer_imports_ignora_from_relativo_sin_modulo() -> None:
    tree = compile("from . import algo", "<src>", "exec", flags=0x400)
    assert _extraer_imports(tree) == []


@pytest.mark.parametrize(
    ("capa", "imported", "esperado"),
    [
        ("ui", "app.infrastructure.repo", True),
        ("ui", "app.infrastructurealgo", True),
        ("application", "app.infrastructure.repo", False),
    ],
)
def test_regla_ui_no_depende_infra(capa: str, imported: str, esperado: bool) -> None:
    assert _regla_ui_no_depende_infra(capa, imported) is esperado


@pytest.mark.parametrize(
    ("capa", "imported", "esperado"),
    [
        ("domain", "app.infrastructure.db", True),
        ("domain", "app.infrastructure_extra", True),
        ("ui", "app.infrastructure.db", False),
    ],
)
def test_regla_domain_no_depende_infra(capa: str, imported: str, esperado: bool) -> None:
    assert _regla_domain_no_depende_infra(capa, imported) is esperado


@pytest.mark.parametrize(
    ("capa", "imported", "esperado"),
    [
        ("domain", "app.ui.widgets", True),
        ("domain", "app.ui_legacy", True),
        ("application", "app.ui.widgets", False),
    ],
)
def test_regla_domain_no_depende_ui(capa: str, imported: str, esperado: bool) -> None:
    assert _regla_domain_no_depende_ui(capa, imported) is esperado


def test_evaluar_reglas_arquitectura_sin_violaciones_devuelve_pass() -> None:
    fs = FSBuilder({"/repo/app/domain/modelo.py": "import app.application.casos"})

    resultado = evaluar_reglas_arquitectura(fs, Path("/repo"))

    assert resultado.id_check == "CHECK-ARQ-001"
    assert resultado.estado is EstadoCheck.PASS
    assert resultado.severidad is SeveridadCheck.ALTO
    assert resultado.evidencia == ["Sin violaciones de imports UI->infra y domain->externo."]


def test_evaluar_reglas_arquitectura_reporta_violaciones_en_formato_esperado() -> None:
    fs = FSBuilder({"/repo/app/ui/vista.py": "import app.infrastructure.repo"})

    resultado = evaluar_reglas_arquitectura(fs, Path("/repo"))

    assert resultado.estado is EstadoCheck.FAIL
    assert resultado.evidencia == ["app/ui/vista.py -> app.infrastructure.repo"]


def test_evaluar_reglas_arquitectura_mantiene_orden_de_violaciones() -> None:
    fs = FSBuilder(
        {
            "/repo/app/domain/modelo.py": "import app.infrastructure.repo\nimport app.ui.pantalla",
            "/repo/app/ui/view.py": "import app.infrastructure.db",
        }
    )

    resultado = evaluar_reglas_arquitectura(fs, Path("/repo"))

    assert resultado.evidencia == [
        "app/domain/modelo.py -> app.infrastructure.repo",
        "app/domain/modelo.py -> app.ui.pantalla",
        "app/ui/view.py -> app.infrastructure.db",
    ]


def test_contrato_orquestador_ejecuta_todas_las_reglas_esperadas(monkeypatch: pytest.MonkeyPatch) -> None:
    llamadas: list[tuple[str, str, str]] = []

    def registrar(nombre: str):
        def _regla(capa: str, imported: str) -> bool:
            llamadas.append((nombre, capa, imported))
            return False

        return _regla

    monkeypatch.setattr("app.application.auditoria_e2e.reglas._regla_ui_no_depende_infra", registrar("ui_infra"))
    monkeypatch.setattr("app.application.auditoria_e2e.reglas._regla_domain_no_depende_infra", registrar("domain_infra"))
    monkeypatch.setattr("app.application.auditoria_e2e.reglas._regla_domain_no_depende_ui", registrar("domain_ui"))

    fs = FSBuilder({"/repo/app/domain/modelo.py": "import app.infrastructure.repo\nimport app.ui.vistas"})

    resultado = evaluar_reglas_arquitectura(fs, Path("/repo"))

    assert resultado.estado is EstadoCheck.PASS
    assert len(llamadas) == 6
    assert [nombre for nombre, _, _ in llamadas[:3]] == ["ui_infra", "domain_infra", "domain_ui"]
    assert [nombre for nombre, _, _ in llamadas[3:]] == ["ui_infra", "domain_infra", "domain_ui"]


def test_contrato_orquestador_formato_de_evidencia_y_recomendacion_estables() -> None:
    fs = FSBuilder({"/repo/app/domain/modelo.py": "from app.ui.panel import Panel"})

    resultado = evaluar_reglas_arquitectura(fs, Path("/repo"))

    assert resultado.evidencia == ["app/domain/modelo.py -> app.ui.panel"]
    assert resultado.recomendacion == "Mantener dependencias dirigidas a puertos y casos de uso en application."
