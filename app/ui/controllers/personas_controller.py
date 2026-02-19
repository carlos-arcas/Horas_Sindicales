from __future__ import annotations

from app.domain.services import ValidacionError


class PersonasController:
    def __init__(self, window) -> None:
        self.window = window

    def on_add_persona(self, persona_dto) -> None:
        w = self.window
        try:
            creada = w._persona_use_cases.crear(persona_dto)
        except ValidacionError as exc:
            w.toast.warning(str(exc), title="Validación")
            return
        w._load_personas(select_id=creada.id)
