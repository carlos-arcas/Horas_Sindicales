from __future__ import annotations


class PdfController:
    def __init__(self, solicitud_use_cases) -> None:
        self._solicitud_use_cases = solicitud_use_cases

    def sugerir_nombre_historico(self, filtro):
        return self._solicitud_use_cases.sugerir_nombre_pdf_historico(filtro)
