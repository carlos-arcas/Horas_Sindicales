# Evidencia de quality gate y cobertura

## Comandos ejecutados en esta rama

```bash
ruff check .
pytest -q tests/infrastructure/test_sheets_errors_unit.py tests/infrastructure/test_sheets_client_puros_unit.py tests/infrastructure/test_health_probes_unit.py tests/infrastructure/test_sheets_rate_limit.py tests/test_quality_gate_preflight.py
python scripts/quality_gate.py
python scripts/report_quality.py --out logs/quality_report.txt
```

## Resultado resumido

- `ruff check .`: OK.
- Suite focalizada de infraestructura + preflight: `33 passed`.
- `scripts/quality_gate.py`: falla de forma controlada si `pytest-cov` no está instalado, con mensaje accionable.
- `logs/quality_report.txt` regenerado correctamente.

## Cobertura

En este entorno no se pudo ejecutar cobertura por ausencia de `pytest-cov` y `coverage.py`.
El preflight ahora falla explícitamente con instrucción de instalación (`python -m pip install -r requirements-dev.txt`).

### Comando canónico para obtener TOTAL y cobertura por paquete

```bash
pytest -q -m "not ui" --cov=. --cov-report=term-missing
python scripts/report_quality.py --out logs/quality_report.txt
```

Al ejecutarlo con dependencias dev instaladas, debe reportar:

- `TOTAL` (bloque de `pytest-cov`).
- `application` e `infrastructure` en `logs/quality_report.txt`.
