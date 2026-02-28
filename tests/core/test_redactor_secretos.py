from __future__ import annotations

import logging

from app.core.redactor_secretos import LoggingSecretsFilter, redactar_texto


def test_redactar_texto_redacta_access_token() -> None:
    redacted = redactar_texto("access_token=abc123")

    assert "abc123" not in redacted
    assert "<REDACTED>" in redacted


def test_redactar_texto_redacta_private_key_json() -> None:
    payload = '{"private_key": "-----BEGIN PRIVATE KEY-----dummy-----END PRIVATE KEY-----"}'

    redacted = redactar_texto(payload)

    assert "BEGIN PRIVATE KEY" not in redacted
    assert '"private_key": <REDACTED>' in redacted


def test_filter_redacta_tokens_en_output(caplog) -> None:
    logger_name = "tests.redactor_secretos"
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)
    for existing_filter in list(logger.filters):
        logger.removeFilter(existing_filter)
    logger.addFilter(LoggingSecretsFilter())

    with caplog.at_level(logging.INFO, logger=logger_name):
        logger.info("authorization: bearer dummy-secret-token")

    assert caplog.records
    assert "dummy-secret-token" not in caplog.text
    assert "<REDACTED>" in caplog.text
