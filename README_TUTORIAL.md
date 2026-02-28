# README_TUTORIAL

## Demo headless en 3 comandos (sin credenciales reales)

```bash
python -m pytest -q tests/application/test_pull_planner.py tests/application/test_push_builder.py
python -m pytest -q tests/application/test_sync_snapshots.py tests/application/test_sync_reporting_rules.py
python -m pytest -q tests/application/test_sync_sheets_use_case_planner_runner_contract.py
```

> Estos tests ejercitan planner/runner/builder y reglas puras sin abrir UI ni depender de Google Sheets real.

## Ejecutar tests core

```bash
make test
```

Alternativa directa:

```bash
PYTHONPATH=. pytest -q
```

## Cómo leer logs y quality_report

1. Ejecuta el gate:
   ```bash
   make quality
   ```
2. Revisa salida consolidada:
   - `logs/quality_report.txt` (reporte técnico principal)
   - `logs/summary.txt` (resumen rápido)
3. Para foco por símbolo/función:
   ```bash
   python scripts/report_quality.py --target app/application/use_cases/sync_sheets/use_case.py:SheetsSyncService._pull_solicitudes_worksheet
   ```
