from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.application.use_cases.confirmacion_pdf.modelos import SolicitudConfirmarPdfResultado
from app.ui.copy_catalog import copy_text
from app.ui.vistas.confirmacion_orquestacion import ResultadoConfirmacionFlujo, execute_confirmar_with_pdf, run_confirmacion_plan


@dataclass
class SolicitudFalsa:
    id: int | None


@dataclass
class PersonaFalsa:
    id: int | None


class VentanaFalsa:
    def __init__(self, *, selected_ids: list[int | None], selected: list[SolicitudFalsa], persona: PersonaFalsa | None, pdf_path: str | None) -> None:
        self._ui_ready = True
        self._pending_conflict_rows: set[int] = set()
        self._run_preconfirm_checks = lambda: True
        self.selected_ids = selected_ids
        self.selected = selected
        self.persona = persona
        self.pdf_path = pdf_path

        self.prompt_calls = 0
        self.confirm_calls = 0
        self.finalize_calls = 0
        self.feedback: list[tuple[str | None, str | None]] = []
        self.outcome: Any = None
        self.refrescos: list[str] = []

    def apply_show_error(self, _window: Any, action: Any) -> None:
        self.feedback.append((action.message, action.title))

    def apply_prompt_pdf(self, _window: Any, _selected: list[SolicitudFalsa]) -> str | None:
        self.prompt_calls += 1
        return self.pdf_path

    def apply_confirm(self, _window: Any, _persona: PersonaFalsa | None, _selected: list[SolicitudFalsa], _pdf_path: str | None):
        self.confirm_calls += 1
        if self.pdf_path is None:
            return None
        ids = [sid for sid in self.selected_ids if sid is not None]
        self.outcome = ResultadoConfirmacionFlujo(
            correlation_id="corr-1",
            resultado=SolicitudConfirmarPdfResultado(
                estado="OK_CON_PDF",
                confirmadas=len(ids),
                confirmadas_ids=ids,
                errores=[],
                pdf_generado=Path(self.pdf_path),
                sync_permitido=True,
                pendientes_restantes=[],
            ),
            creadas=[],
            pendientes_restantes=[],
        )
        return self.outcome

    def apply_finalize(self, _window: Any, _persona: PersonaFalsa | None, outcome: Any) -> None:
        self.finalize_calls += 1
        assert outcome == self.outcome
        self.refrescos.extend(["pendientes", "historico", "saldos"])


def _ejecutar_plan(window: VentanaFalsa) -> None:
    run_confirmacion_plan(
        window,
        selected=window.selected,
        selected_ids=window.selected_ids,
        persona=window.persona,
        log_extra={},
        apply_show_error=window.apply_show_error,
        apply_prompt_pdf=window.apply_prompt_pdf,
        apply_confirm=window.apply_confirm,
        apply_finalize=window.apply_finalize,
    )


def test_contrato_confirmar_pdf_desde_ui_sin_seleccion() -> None:
    window = VentanaFalsa(selected_ids=[], selected=[], persona=PersonaFalsa(id=1), pdf_path="/tmp/ok.pdf")

    _ejecutar_plan(window)

    assert window.prompt_calls == 0
    assert window.confirm_calls == 0
    assert window.finalize_calls == 0
    assert window.feedback


def test_contrato_confirmar_pdf_desde_ui_con_cancelacion_de_guardado() -> None:
    seleccion = [SolicitudFalsa(id=7)]
    window = VentanaFalsa(selected_ids=[7], selected=seleccion, persona=PersonaFalsa(id=1), pdf_path=None)

    _ejecutar_plan(window)

    assert window.prompt_calls == 1
    assert window.confirm_calls == 0
    assert window.finalize_calls == 0
    assert window.outcome is None
    assert window.refrescos == []


def test_contrato_confirmar_pdf_desde_ui_con_ruta_valida() -> None:
    seleccion = [SolicitudFalsa(id=7)]
    window = VentanaFalsa(selected_ids=[7], selected=seleccion, persona=PersonaFalsa(id=1), pdf_path="/tmp/ok.pdf")

    _ejecutar_plan(window)

    assert window.prompt_calls == 1
    assert window.confirm_calls == 1
    assert window.finalize_calls == 1
    assert window.outcome is not None
    assert window.refrescos == ["pendientes", "historico", "saldos"]


class VentanaSinCasoUso:
    def __init__(self) -> None:
        self._pending_all_solicitudes = []
        self._set_processing_state_calls: list[bool] = []
        self.errores_criticos: list[Exception] = []

    def _set_processing_state(self, valor: bool) -> None:
        self._set_processing_state_calls.append(valor)

    def _show_critical_error(self, exc: Exception) -> None:
        self.errores_criticos.append(exc)

    @property
    def _solicitudes_controller(self):
        raise AssertionError("La vista no debe usar _solicitudes_controller en confirmar+PDF.")


def test_execute_confirmar_pdf_falla_si_no_hay_caso_uso_configurado() -> None:
    window = VentanaSinCasoUso()

    resultado = execute_confirmar_with_pdf(
        window,
        persona=PersonaFalsa(id=1),
        selected=[SolicitudFalsa(id=7)],
        pdf_path="/tmp/ok.pdf",
    )

    assert resultado is None
    assert window._set_processing_state_calls == [True, False]
    assert len(window.errores_criticos) == 1
    assert str(window.errores_criticos[0]) == copy_text("ui.errores.error_inesperado")
