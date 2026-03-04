from __future__ import annotations

from app.application.base_cuadrantes_service import BaseCuadrantesService
from app.domain.base_cuadrantes import DEFAULT_BASE_DIAS, default_base_minutes
from app.domain.models import Persona


class PersonaRepoFake:
    def __init__(self, personas: dict[int, Persona], uuids: dict[int, str | None]) -> None:
        self._personas = personas
        self._uuids = uuids
        self.actualizaciones: list[Persona] = []

    def list_all(self, include_inactive: bool = False):
        return self._personas.values()

    def get_by_id(self, persona_id: int) -> Persona | None:
        return self._personas.get(persona_id)

    def get_or_create_uuid(self, persona_id: int) -> str | None:
        return self._uuids.get(persona_id)

    def update(self, persona: Persona) -> Persona:
        assert persona.id is not None
        self._personas[persona.id] = persona
        self.actualizaciones.append(persona)
        return persona


class CuadranteRepoFake:
    def __init__(self, existentes: set[tuple[str, str]] | None = None) -> None:
        self._existentes = existentes or set()
        self.creados: list[tuple[str, str, int, int]] = []

    def exists_for_delegada(self, delegada_uuid: str, dia_semana: str) -> bool:
        return (delegada_uuid, dia_semana) in self._existentes

    def create(self, delegada_uuid: str, dia_semana: str, man_min: int, tar_min: int) -> None:
        self.creados.append((delegada_uuid, dia_semana, man_min, tar_min))


def _persona(id_: int | None, valor: int = 0) -> Persona:
    return Persona(
        id=id_,
        nombre="Delegada",
        genero="F",
        horas_mes_min=0,
        horas_ano_min=0,
        is_active=True,
        cuad_lun_man_min=valor,
        cuad_lun_tar_min=0,
        cuad_mar_man_min=valor,
        cuad_mar_tar_min=0,
        cuad_mie_man_min=valor,
        cuad_mie_tar_min=0,
        cuad_jue_man_min=valor,
        cuad_jue_tar_min=0,
        cuad_vie_man_min=valor,
        cuad_vie_tar_min=0,
        cuad_sab_man_min=valor,
        cuad_sab_tar_min=0,
        cuad_dom_man_min=valor,
        cuad_dom_tar_min=0,
    )


def test_ensure_for_persona_crea_base_y_respeta_dias_existentes() -> None:
    repo_persona = PersonaRepoFake({7: _persona(7)}, {7: "uuid-7"})
    repo_cuadrante = CuadranteRepoFake({("uuid-7", "lun")})

    servicio = BaseCuadrantesService(repo_persona, repo_cuadrante)
    servicio.ensure_for_persona(7)

    man, tar = default_base_minutes()
    assert len(repo_persona.actualizaciones) == 1
    assert len(repo_cuadrante.creados) == len(DEFAULT_BASE_DIAS) - 1
    assert ("uuid-7", "mar", man, tar) in repo_cuadrante.creados


def test_ensure_for_persona_sale_temprano_si_persona_o_uuid_no_existen() -> None:
    repo_persona = PersonaRepoFake({1: _persona(1)}, {1: None})
    repo_cuadrante = CuadranteRepoFake()
    servicio = BaseCuadrantesService(repo_persona, repo_cuadrante)

    servicio.ensure_for_persona(999)
    servicio.ensure_for_persona(1)

    assert repo_persona.actualizaciones == []
    assert repo_cuadrante.creados == []


def test_ensure_for_all_personas_omite_ids_none() -> None:
    repo_persona = PersonaRepoFake({1: _persona(1), 2: _persona(None)}, {1: "uuid-1"})
    repo_cuadrante = CuadranteRepoFake()

    servicio = BaseCuadrantesService(repo_persona, repo_cuadrante)
    servicio.ensure_for_all_personas()

    assert all(reg[0] == "uuid-1" for reg in repo_cuadrante.creados)
