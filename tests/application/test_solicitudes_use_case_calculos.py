from __future__ import annotations

import pytest

from app.application.dto import PeriodoFiltro, SolicitudDTO
from app.application.use_cases import SolicitudUseCases
from app.domain.models import Persona
from app.domain.services import BusinessRuleError
from app.infrastructure.repos_sqlite import PersonaRepositorySQLite, SolicitudRepositorySQLite


def _crear_persona(persona_repo: PersonaRepositorySQLite, *, horas_mes: int = 600, horas_ano: int = 7200) -> int:
    persona = persona_repo.create(
        Persona(
            id=None,
            nombre="Delegada Cálculos",
            genero="F",
            horas_mes_min=horas_mes,
            horas_ano_min=horas_ano,
            is_active=True,
            cuad_lun_man_min=240,
            cuad_lun_tar_min=240,
            cuad_mar_man_min=240,
            cuad_mar_tar_min=240,
            cuad_mie_man_min=240,
            cuad_mie_tar_min=240,
            cuad_jue_man_min=240,
            cuad_jue_tar_min=240,
            cuad_vie_man_min=240,
            cuad_vie_tar_min=240,
            cuad_sab_man_min=0,
            cuad_sab_tar_min=0,
            cuad_dom_man_min=0,
            cuad_dom_tar_min=0,
        )
    )
    return int(persona.id or 0)


def _dto_valido(persona_id: int, *, desde: str = "09:00", hasta: str = "11:00", horas: float = 0.0) -> SolicitudDTO:
    return SolicitudDTO(
        id=None,
        persona_id=persona_id,
        fecha_solicitud="2025-01-10",
        fecha_pedida="2025-01-15",
        desde=desde,
        hasta=hasta,
        completo=False,
        horas=horas,
        observaciones="Obs",
        pdf_path=None,
        pdf_hash=None,
        notas="Nota",
    )


def test_calcular_minutos_solicitud_ok(connection) -> None:
    persona_repo = PersonaRepositorySQLite(connection)
    solicitud_repo = SolicitudRepositorySQLite(connection)
    persona_id = _crear_persona(persona_repo)
    use_case = SolicitudUseCases(solicitud_repo, persona_repo)

    minutos = use_case.calcular_minutos_solicitud(_dto_valido(persona_id))

    assert minutos == 120


def test_calcular_minutos_solicitud_error_persona_inexistente(connection) -> None:
    persona_repo = PersonaRepositorySQLite(connection)
    solicitud_repo = SolicitudRepositorySQLite(connection)
    use_case = SolicitudUseCases(solicitud_repo, persona_repo)

    with pytest.raises(BusinessRuleError, match="Persona no encontrada"):
        use_case.calcular_minutos_solicitud(_dto_valido(99999))


def test_calcular_minutos_solicitud_error_horas_negativas(connection) -> None:
    persona_repo = PersonaRepositorySQLite(connection)
    solicitud_repo = SolicitudRepositorySQLite(connection)
    persona_id = _crear_persona(persona_repo)
    use_case = SolicitudUseCases(solicitud_repo, persona_repo)

    with pytest.raises(BusinessRuleError, match="horas"):
        use_case.calcular_minutos_solicitud(_dto_valido(persona_id, horas=-1.0))


def test_calcular_saldos_por_periodo_sin_solicitudes(connection) -> None:
    persona_repo = PersonaRepositorySQLite(connection)
    solicitud_repo = SolicitudRepositorySQLite(connection)
    persona_id = _crear_persona(persona_repo, horas_mes=300, horas_ano=4000)
    use_case = SolicitudUseCases(solicitud_repo, persona_repo)

    saldos = use_case.calcular_saldos_por_periodo(persona_id, PeriodoFiltro.mensual(2025, 1))

    assert saldos.consumidas_mes == 0
    assert saldos.restantes_mes == 300
    assert saldos.consumidas_ano == 0
    assert saldos.restantes_ano == 4000


def test_calcular_saldos_por_periodo_con_solicitudes(connection) -> None:
    persona_repo = PersonaRepositorySQLite(connection)
    solicitud_repo = SolicitudRepositorySQLite(connection)
    persona_id = _crear_persona(persona_repo, horas_mes=300, horas_ano=4000)
    use_case = SolicitudUseCases(solicitud_repo, persona_repo)

    creada, _ = use_case.agregar_solicitud(_dto_valido(persona_id))
    assert creada.id is not None
    solicitud_repo.mark_generated(int(creada.id), True)

    saldos = use_case.calcular_saldos_por_periodo(persona_id, PeriodoFiltro.mensual(2025, 1))

    assert saldos.consumidas_mes == 120
    assert saldos.restantes_mes == 180


def test_calcular_saldos_por_periodo_propaga_error_de_repo(connection, monkeypatch: pytest.MonkeyPatch) -> None:
    persona_repo = PersonaRepositorySQLite(connection)
    solicitud_repo = SolicitudRepositorySQLite(connection)
    persona_id = _crear_persona(persona_repo)
    use_case = SolicitudUseCases(solicitud_repo, persona_repo)

    def _falla_repo(*_args, **_kwargs):
        raise RuntimeError("fallo de consulta")

    monkeypatch.setattr(solicitud_repo, "list_by_persona_and_period", _falla_repo)

    with pytest.raises(RuntimeError, match="fallo de consulta"):
        use_case.calcular_saldos_por_periodo(persona_id, PeriodoFiltro.mensual(2025, 1))
