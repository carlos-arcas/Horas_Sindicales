from __future__ import annotations

from app.domain.models import Solicitud


def test_repos_sqlite_persisten_datos_en_memoria(persona_repo, solicitud_repo, persona_id) -> None:
    persona = persona_repo.get_by_id(persona_id)
    assert persona is not None
    assert persona.nombre == "Delegada Fixture"

    creada = solicitud_repo.create(
        Solicitud(
            id=None,
            persona_id=persona_id,
            fecha_solicitud="2025-01-01",
            fecha_pedida="2025-01-20",
            desde_min=480,
            hasta_min=600,
            completo=False,
            horas_solicitadas_min=120,
            observaciones="persistencia",
            notas="sqlite-memory",
        )
    )

    assert creada.id is not None
    solicitud_repo.update_pdf_info(creada.id, "/tmp/persist.pdf", "hash-persist")
    solicitud_persistida = solicitud_repo.get_by_id(creada.id)
    assert solicitud_persistida is not None
    assert solicitud_persistida.notas == "sqlite-memory"

    solicitudes_mes = list(solicitud_repo.list_by_persona_and_period(persona_id, 2025, 1))
    assert len(solicitudes_mes) == 1
