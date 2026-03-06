from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypeAlias

from PySide6.QtWidgets import QFileDialog, QMessageBox

from app.bootstrap.logging import log_operational_error
from app.ui.copy_catalog import copy_text
from app.ui.vistas.ui_helpers import abrir_archivo_local, abrir_carpeta_contenedora

if TYPE_CHECKING:
    from app.application.dto import PersonaDTO, SolicitudDTO
    from app.ui.vistas.confirmacion_presenter import ConfirmAction

logger = logging.getLogger(__name__)
ResultadoConfirmacionPdf: TypeAlias = tuple[
    str | None,
    Path | None,
    list["SolicitudDTO"],
    list[int],
    list[str],
    list["SolicitudDTO"] | None,
]


def prompt_confirm_pdf_path(window: Any, selected: list[SolicitudDTO]) -> str | None:
    default_name = window._solicitud_use_cases.sugerir_nombre_pdf(selected)
    default_path = str(Path.home() / default_name)
    pdf_path, _ = QFileDialog.getSaveFileName(
        window,
        copy_text("ui.confirmacion.guardar_pdf"),
        default_path,
        copy_text("ui.confirmacion.filtro_pdf"),
    )
    if not pdf_path:
        return None
    return resolver_colision_destino_pdf(window, pdf_path)


def resolver_colision_destino_pdf(window: Any, pdf_path: str) -> str | None:
    resolucion = window._solicitudes_controller.obtener_resolucion_destino_pdf(pdf_path)
    if not resolucion.colision_detectada:
        return str(resolucion.ruta_destino)
    alternativa = resolucion.ruta_alternativa
    dialog = QMessageBox(window)
    dialog.setIcon(QMessageBox.Icon.Warning)
    dialog.setWindowTitle(copy_text("ui.confirmacion.archivo_ya_existe_titulo"))
    dialog.setText(copy_text("ui.confirmacion.archivo_ya_existe_texto"))
    dialog.setInformativeText(copy_text("ui.confirmacion.archivo_ya_existe_info"))
    rename_button = _add_rename_button(dialog, alternativa)
    change_folder_button = dialog.addButton(copy_text("ui.confirmacion.cambiar_carpeta"), QMessageBox.ButtonRole.ActionRole)
    overwrite_button = dialog.addButton(copy_text("ui.confirmacion.sobrescribir"), QMessageBox.ButtonRole.DestructiveRole)
    cancel_button = dialog.addButton(copy_text("ui.confirmacion.cancelar"), QMessageBox.ButtonRole.RejectRole)
    dialog.exec()
    clicked = dialog.clickedButton()
    if rename_button is not None and clicked is rename_button:
        return str(alternativa)
    if clicked is overwrite_button:
        return str(resolucion.ruta_original)
    if clicked is change_folder_button:
        return prompt_confirm_pdf_path(window, window._selected_pending_solicitudes())
    if clicked is cancel_button:
        return None
    return None


def _add_rename_button(dialog: QMessageBox, alternativa: Path | None) -> Any:
    if alternativa is None:
        return None
    return dialog.addButton(
        copy_text("ui.confirmacion.guardar_como", nombre=alternativa.name),
        QMessageBox.ButtonRole.AcceptRole,
    )


def show_pdf_actions_dialog(window: Any, generated_path: Path) -> None:
    if not generated_path.exists():
        return
    dialog = QMessageBox(window)
    dialog.setWindowTitle(copy_text("ui.confirmacion.pdf_generado_titulo"))
    dialog.setText(copy_text("ui.confirmacion.ok_pdf_generado"))
    open_pdf_button = dialog.addButton(copy_text("ui.confirmacion.abrir_pdf"), QMessageBox.ButtonRole.ActionRole)
    open_folder_button = dialog.addButton(copy_text("ui.confirmacion.abrir_carpeta"), QMessageBox.ButtonRole.ActionRole)
    close_button = dialog.addButton(copy_text("ui.confirmacion.cerrar"), QMessageBox.ButtonRole.RejectRole)
    dialog.exec()
    clicked = dialog.clickedButton()
    if clicked is open_pdf_button:
        abrir_archivo_local(generated_path)
    elif clicked is open_folder_button:
        abrir_carpeta_contenedora(generated_path)
    elif clicked is close_button:
        return


def ask_push_after_pdf(window: Any) -> None:
    dialog = QMessageBox(window)
    dialog.setWindowTitle(copy_text("ui.confirmacion.pdf_generado_titulo"))
    dialog.setText(copy_text("ui.confirmacion.sync_despues_pdf_pregunta"))
    subir_button = dialog.addButton(copy_text("ui.confirmacion.subir_ahora"), QMessageBox.AcceptRole)
    dialog.addButton(copy_text("ui.confirmacion.mas_tarde"), QMessageBox.RejectRole)
    dialog.exec()
    if dialog.clickedButton() == subir_button:
        window._on_push_now()


def apply_show_error(window: Any, action: ConfirmAction) -> None:
    if action.message:
        window.toast.warning(action.message, title=action.title or copy_text("ui.validacion.validacion"))


def apply_prompt_pdf(window: Any, selected: list[SolicitudDTO]) -> str | None:
    if not selected:
        window.toast.warning(copy_text("ui.confirmacion.sin_seleccion"), title=copy_text("ui.validacion.validacion"))
        return None
    pdf_path = window._prompt_confirm_pdf_path(selected)
    logger.info("UI_CONFIRMAR_PDF_SAVE_PATH_CHOSEN", extra={"pdf_path": pdf_path, "selected_ids_count": len(selected)})
    window._last_selected_pdf_path = pdf_path
    if pdf_path is None:
        return None
    if not pdf_path:
        window.toast.warning(copy_text("ui.confirmacion.pdf_destino_obligatorio"), title=copy_text("ui.validacion.validacion"))
    return pdf_path


def apply_confirm(window: Any, persona: PersonaDTO | None, selected: list[SolicitudDTO], pdf_path: str | None) -> ResultadoConfirmacionPdf | None:
    if persona is None or pdf_path is None:
        return None
    try:
        resultado = window._execute_confirmar_with_pdf(persona, selected, pdf_path)
        logger.info("UI_CONFIRMAR_PDF_EXECUTE_OK", extra={"selected_ids_count": len(selected), "pdf_path": pdf_path})
        return resultado
    except Exception as exc:
        logger.exception("UI_CONFIRMAR_PDF_EXECUTE_ERROR")
        log_operational_error(
            logger,
            "UI_CONFIRMAR_GENERAR_PDF_FALLO",
            exc=exc,
            extra={"selected_ids_count": len(selected), "pdf_path": pdf_path},
        )
        window._set_processing_state(False)
        window._toast_error(copy_text("ui.confirmacion.error_generar_pdf"), title=copy_text("ui.validacion.validacion"))
        return None


def apply_finalize(window: Any, persona: PersonaDTO | None, outcome: ResultadoConfirmacionPdf | None) -> None:
    if persona is None or outcome is None:
        logger.info(
            "UI_CONFIRMAR_TOAST_SUCCESS_DESCARTADO",
            extra={"motivo": "sin_persona_o_sin_outcome"},
        )
        return
    correlation_id, generado, creadas, confirmadas_ids, errores, pendientes_restantes = outcome
    logger.debug("_on_confirmar paso=resultado_execute pdf_generado=%s", str(generado) if generado else None)
    window._finalize_confirmar_with_pdf(persona, correlation_id, generado, creadas, confirmadas_ids, errores, pendientes_restantes)
    logger.info(
        "UI_CONFIRMAR_PDF_OK",
        extra={
            "persona_id": persona.id if persona is not None else None,
            "confirmadas_count": len(confirmadas_ids),
            "errores_count": len(errores),
            "pdf_generado": bool(generado),
            "correlation_id": correlation_id,
        },
    )
    if generado is not None and generado.exists():
        window._toast_success(copy_text("ui.confirmacion.ok_pdf_generado"), title=copy_text("ui.preferencias.confirmacion"))
        return

    logger.warning(
        "UI_CONFIRMAR_TOAST_SUCCESS_DESCARTADO",
        extra={
            "motivo": "pdf_no_generado_o_inexistente",
            "pdf_generado": bool(generado),
            "correlation_id": correlation_id,
            "confirmadas_count": len(confirmadas_ids),
            "errores_count": len(errores),
        },
    )
