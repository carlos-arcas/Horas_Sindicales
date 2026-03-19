# Guía de contribución

Este repositorio mantiene una **aplicación desktop en Python + PySide6**.
Cada cambio debe ayudar a ejecutar la app, mantenerla, probarla o auditarla.
Si algo no cumple una de esas funciones, no debería entrar al árbol activo.

## Alcance esperado de un PR

- Un problema por PR.
- Cambios pequeños y verificables.
- Sin mezclar limpieza, feature y bugfix si no comparten la misma causa.
- Si tocas comportamiento visible, añade o ajusta tests.

## Flujo mínimo

1. Crea una rama desde `main`.
2. Implementa el cambio con naming en español y respetando Clean Architecture.
3. Ejecuta el gate canónico local: `python -m scripts.gate_pr`.
4. Si el gate falla, corrige y repite antes de abrir PR.
5. Documenta solo lo necesario para operar, mantener o auditar el cambio.

## Reglas obligatorias

- `dominio/` no depende de UI ni infraestructura.
- `app/domain` y `app/application` no deben arrastrar PySide6.
- No introducir texto visible hardcodeado en UI.
- No dejar archivos `legacy`, `old`, `bak`, `copy`, `tmp` o equivalentes.
- No subir documentación placeholder ni marketing interno.
- Mantener logging estructurado si el cambio afecta ejecución, errores o auditoría.

## Comandos oficiales

```bash
python -m scripts.gate_rapido
python -m scripts.gate_pr
```

Comprobaciones útiles adicionales:

```bash
pytest -q -m "not ui"
pytest -q tests/golden/botones
python -m scripts.features_sync
```

## Qué debe explicar el PR

- problema real que corrige;
- riesgo técnico;
- comandos ejecutados;
- impacto documental;
- si hubo limpieza de legacy, qué se borró y por qué no rompía nada.

## Commits

Usa mensajes claros y accionables.
Ejemplos válidos:

- `refactor: elimina historicos fuera del flujo activo`
- `docs: corrige guias de release windows`
- `test: blinda reingreso de residuos legacy`
