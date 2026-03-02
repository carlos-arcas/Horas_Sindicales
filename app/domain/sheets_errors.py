from __future__ import annotations

from app.core.errors import InfraError, TransientExternalError


class SheetsConfigError(InfraError):
    pass


class SheetsApiDisabledError(SheetsConfigError):
    pass


class SheetsPermissionError(SheetsConfigError):
    def __init__(
        self,
        message: str,
        *,
        service_account_email: str | None = None,
        spreadsheet_id: str | None = None,
        worksheet: str | None = None,
    ) -> None:
        super().__init__(message)
        self.service_account_email = service_account_email
        self.spreadsheet_id = spreadsheet_id
        self.worksheet = worksheet

    def enriquecer_email_cuenta_servicio(self, service_account_email: str | None) -> "SheetsPermissionError":
        if not service_account_email or self.service_account_email == service_account_email:
            return self
        return SheetsPermissionError(
            self.args[0],
            service_account_email=service_account_email,
            spreadsheet_id=self.spreadsheet_id,
            worksheet=self.worksheet,
        )

    def with_context(
        self,
        *,
        spreadsheet_id: str | None = None,
        worksheet: str | None = None,
    ) -> "SheetsPermissionError":
        resolved_spreadsheet_id = spreadsheet_id or self.spreadsheet_id
        resolved_worksheet = worksheet or self.worksheet
        if resolved_spreadsheet_id == self.spreadsheet_id and resolved_worksheet == self.worksheet:
            return self
        return SheetsPermissionError(
            self.args[0],
            service_account_email=self.service_account_email,
            spreadsheet_id=resolved_spreadsheet_id,
            worksheet=resolved_worksheet,
        )

    def to_safe_payload(self) -> dict[str, str]:
        payload: dict[str, str] = {}
        if self.spreadsheet_id:
            payload["spreadsheet_id"] = self.spreadsheet_id
        if self.worksheet:
            payload["worksheet"] = self.worksheet
        if self.service_account_email:
            payload["service_account_email"] = self.service_account_email
        return payload

    def __str__(self) -> str:
        details = ", ".join(f"{k}={v}" for k, v in self.to_safe_payload().items())
        if not details:
            return self.args[0]
        return f"{self.args[0]} ({details})"

    def __repr__(self) -> str:
        return (
            "SheetsPermissionError("
            f"message={self.args[0]!r}, "
            f"spreadsheet_id={self.spreadsheet_id!r}, "
            f"worksheet={self.worksheet!r}, "
            f"service_account_email={self.service_account_email!r}"
            ")"
        )


def construir_mensaje_permiso_sheets(error: SheetsPermissionError) -> str:
    """Construye una ayuda accionable y estable para i18n sobre errores 403 de Sheets."""
    spreadsheet_id = error.spreadsheet_id or "desconocido"
    worksheet = error.worksheet or "desconocida"
    service_account_email = error.service_account_email or "cuenta_de_servicio_no_disponible"
    return (
        "i18n_key=sync.permission_denied; "
        f"spreadsheet_id={spreadsheet_id}; "
        f"worksheet={worksheet}; "
        f"service_account_email={service_account_email}; "
        "ayuda=Comparte la hoja con la cuenta de servicio como Editor y reintenta la sincronización."
    )


class SheetsNotFoundError(SheetsConfigError):
    pass


class SheetsCredentialsError(SheetsConfigError):
    pass


class SheetsRateLimitError(TransientExternalError):
    pass
