from __future__ import annotations

from app.core.errors import InfraError, TransientExternalError


class SheetsConfigError(InfraError):
    pass


class SheetsApiDisabledError(SheetsConfigError):
    pass


class SheetsPermissionError(SheetsConfigError):
    def __init__(self, message: str, *, service_account_email: str | None = None) -> None:
        super().__init__(message)
        self.service_account_email = service_account_email

    def with_service_account_email(self, service_account_email: str | None) -> "SheetsPermissionError":
        if not service_account_email or self.service_account_email == service_account_email:
            return self
        return SheetsPermissionError(str(self), service_account_email=service_account_email)


class SheetsNotFoundError(SheetsConfigError):
    pass


class SheetsCredentialsError(SheetsConfigError):
    pass


class SheetsRateLimitError(TransientExternalError):
    pass
