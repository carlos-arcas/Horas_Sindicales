# Contrato de wiring: cómo funciona

Se añadió un contrato de tests para evitar fallos de arranque por handlers faltantes o firmas incompatibles en conexiones de señales Qt.

## Qué valida

- Recorre con AST los archivos de wiring en:
  - `app/ui/vistas/builders/**/*.py`
  - `app/ui/vistas/main_window/**/*.py`
- Detecta referencias de handlers en:
  - `window.<widget>.<signal>.connect(window.<handler>)`
  - `conectar_signal(window, <signal>, "<handler_name>", ...)`
- Falla si un handler referenciado no existe en `MainWindow` (incluyendo MRO/bindings de clase).
- Verifica firmas para señales Qt con argumento (`dateChanged`, `timeChanged`, `toggled`), exigiendo al menos un argumento adicional a `self` o `*args`.
- Incluye una validación específica para `on_historico_periodo_mode_changed`.

## Dónde está

- `tests/test_wiring_contract.py`
