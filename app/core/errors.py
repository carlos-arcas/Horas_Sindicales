from __future__ import annotations


class AppError(Exception):
    pass


class BusinessError(AppError):
    pass


class ValidationError(BusinessError):
    pass


class InfraError(AppError):
    pass


class PersistenceError(InfraError):
    pass


class ExternalServiceError(InfraError):
    pass


class TransientExternalError(ExternalServiceError):
    pass
