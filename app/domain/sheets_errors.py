from __future__ import annotations


class SheetsConfigError(Exception):
    pass


class SheetsApiDisabledError(SheetsConfigError):
    pass


class SheetsPermissionError(SheetsConfigError):
    pass


class SheetsNotFoundError(SheetsConfigError):
    pass


class SheetsCredentialsError(SheetsConfigError):
    pass
