from __future__ import annotations

from app.core.errors import InfraError, TransientExternalError


class SheetsConfigError(InfraError):
    pass


class SheetsApiDisabledError(SheetsConfigError):
    pass


class SheetsPermissionError(SheetsConfigError):
    pass


class SheetsNotFoundError(SheetsConfigError):
    pass


class SheetsCredentialsError(SheetsConfigError):
    pass


class SheetsRateLimitError(TransientExternalError):
    pass
