from __future__ import annotations

from dataclasses import replace

import pytest

from app.application.dto import PersonaDTO
from app.application.use_cases.personas.use_case import PersonaUseCases
from app.application.use_cases.politica_modo_solo_lectura import crear_politica_modo_solo_lectura
from app.domain.models import Persona
from app.domain.services import BusinessRuleError


class _RepoPersonasMemoria:
    def __init__(self, personas: list[Persona]) -> None:
        self._personas = {int(p.id or 0): p for p in personas}
        self._uuids = {int(p.id or 0): f"uuid-{int(p.id or 0)}" for p in personas}
        self._next_id = max(self._personas, default=0) + 1

    def list_all(self, include_inactive: bool = False):
        valores = list(self._personas.values())
        if include_inactive:
            return valores
        return [p for p in valores if p.is_active]

    def get_by_id(self, persona_id: int) -> Persona | None:
        return self._personas.get(persona_id)

    def get_by_nombre(self, nombre: str) -> Persona | None:
        return next((p for p in self._personas.values() if p.nombre == nombre), None)

    def create(self, persona: Persona) -> Persona:
        nueva = replace(persona, id=self._next_id)
        self._personas[self._next_id] = nueva
        self._uuids[self._next_id] = f"uuid-{self._next_id}"
        self._next_id += 1
        return nueva

    def update(self, persona: Persona) -> Persona:
        assert persona.id is not None
        self._personas[persona.id] = persona
        return persona

    def get_or_create_uuid(self, persona_id: int) -> str | None:
        if persona_id not in self._personas:
            return None
        return self._uuids.setdefault(persona_id, f"uuid-{persona_id}")


class _BaseCuadrantesSpy:
    def __init__(self) -> None:
        self.ids: list[int] = []

    def ensure_for_persona(self, persona_id: int) -> None:
        self.ids.append(persona_id)


def _persona(persona_id: int, *, activa: bool = True) -> Persona:
    return Persona(
        id=persona_id,
        nombre=f"Delegada {persona_id}",
        genero="F",
        horas_mes_min=600,
        horas_ano_min=7200,
        is_active=activa,
        cuad_lun_man_min=60,
        cuad_lun_tar_min=60,
        cuad_mar_man_min=30,
        cuad_mar_tar_min=30,
        cuad_mie_man_min=30,
        cuad_mie_tar_min=30,
        cuad_jue_man_min=30,
        cuad_jue_tar_min=30,
        cuad_vie_man_min=30,
        cuad_vie_tar_min=30,
        cuad_sab_man_min=15,
        cuad_sab_tar_min=15,
        cuad_dom_man_min=10,
        cuad_dom_tar_min=10,
        cuadrante_uniforme=False,
        trabaja_finde=True,
    )


def _dto_base() -> PersonaDTO:
    return PersonaDTO(
        id=None,
        nombre="Nueva",
        genero="F",
        horas_mes=600,
        horas_ano=7200,
        is_active=True,
        cuad_lun_man_min=50,
        cuad_lun_tar_min=40,
        cuad_mar_man_min=0,
        cuad_mar_tar_min=0,
        cuad_mie_man_min=0,
        cuad_mie_tar_min=0,
        cuad_jue_man_min=0,
        cuad_jue_tar_min=0,
        cuad_vie_man_min=0,
        cuad_vie_tar_min=0,
        cuad_sab_man_min=25,
        cuad_sab_tar_min=25,
        cuad_dom_man_min=20,
        cuad_dom_tar_min=20,
        cuadrante_uniforme=True,
        trabaja_finde=False,
    )


def test_crear_persona_normaliza_cuadrante_uniforme_y_sin_finde() -> None:
    repo = _RepoPersonasMemoria([_persona(1)])
    caso_uso = PersonaUseCases(repo, politica_modo_solo_lectura=crear_politica_modo_solo_lectura(lambda: False))

    creada = caso_uso.crear_persona(_dto_base())

    assert creada.cuad_mar_man_min == creada.cuad_lun_man_min == 50
    assert creada.cuad_vie_tar_min == creada.cuad_lun_tar_min == 40
    assert creada.cuad_sab_man_min == 0
    assert creada.cuad_dom_tar_min == 0


def test_crear_persona_con_base_cuadrantes_refresca_desde_repo() -> None:
    repo = _RepoPersonasMemoria([_persona(1)])
    base_spy = _BaseCuadrantesSpy()
    caso_uso = PersonaUseCases(repo, base_cuadrantes_service=base_spy, politica_modo_solo_lectura=crear_politica_modo_solo_lectura(lambda: False))

    creada = caso_uso.crear_persona(_dto_base())

    assert base_spy.ids == [int(creada.id or 0)]


def test_editar_persona_requiere_id() -> None:
    caso_uso = PersonaUseCases(_RepoPersonasMemoria([_persona(1)]), politica_modo_solo_lectura=crear_politica_modo_solo_lectura(lambda: False))

    with pytest.raises(BusinessRuleError, match="debe tener id"):
        caso_uso.editar_persona(_dto_base())


def test_desactivar_persona_valida_existencia_y_ultima_activa() -> None:
    repo = _RepoPersonasMemoria([_persona(1, activa=True)])
    caso_uso = PersonaUseCases(repo, politica_modo_solo_lectura=crear_politica_modo_solo_lectura(lambda: False))

    with pytest.raises(BusinessRuleError, match="Persona no encontrada"):
        caso_uso.desactivar_persona(99)
    with pytest.raises(BusinessRuleError, match="al menos un delegado activo"):
        caso_uso.desactivar_persona(1)


def test_desactivar_persona_inactiva_devuelve_sin_modificar() -> None:
    repo = _RepoPersonasMemoria([_persona(1, activa=False), _persona(2, activa=True)])
    caso_uso = PersonaUseCases(repo, politica_modo_solo_lectura=crear_politica_modo_solo_lectura(lambda: False))

    dto = caso_uso.desactivar_persona(1)

    assert dto.id == 1
    assert dto.is_active is False


def test_obtener_persona_lanza_error_si_no_existe() -> None:
    caso_uso = PersonaUseCases(_RepoPersonasMemoria([_persona(1)]), politica_modo_solo_lectura=crear_politica_modo_solo_lectura(lambda: False))

    with pytest.raises(BusinessRuleError, match="Persona no encontrada"):
        caso_uso.obtener_persona(8)
