# Proceso de release

Este proyecto utiliza **Semantic Versioning (SemVer)** y un flujo reproducible de validación antes de publicar una versión.

## 1) Cómo decidir el bump de versión

Usar `MAJOR.MINOR.PATCH`:

- **MAJOR** (`X.0.0`): cambios incompatibles con versiones anteriores.
- **MINOR** (`x.Y.0`): nuevas capacidades compatibles hacia atrás.
- **PATCH** (`x.y.Z`): correcciones compatibles hacia atrás.

Regla práctica:

- Si rompes contratos o interfaces: bump **major**.
- Si agregas funcionalidad sin romper contratos: bump **minor**.
- Si corriges bugs/refactors internos sin romper contratos: bump **patch**.

## 2) Actualizar versión y changelog

1. Editar `app/__init__.py` y actualizar `__version__`.
2. Mover/organizar entradas de `CHANGELOG.md` desde `[Unreleased]` a `[{nueva_version}]`.
3. Mantener secciones `Added`, `Changed`, `Fixed` para la nueva versión.

## 3) Ejecutar validación de release

Comando único:

```bash
make release-check
```

Este comando ejecuta `scripts/release/release.py`, que valida:

- Árbol de git limpio.
- `__version__` con formato SemVer.
- Sección de versión en `CHANGELOG.md`.
- Calidad mínima: ejecutar `python scripts/quality_gate.py` (lee el umbral desde `.config/quality_gate.json`).

## 4) Crear tag de versión

Cuando `make release-check` pase:

```bash
git tag vX.Y.Z
git push --tags
```

Luego crear el Release en GitHub para `vX.Y.Z` con notas basadas en `CHANGELOG.md`.

## 5) Verificación de artefactos

Para release Windows, se pueden usar los scripts existentes en `scripts/release/`:

- `00_check_prereqs.bat`
- `10_setup_venv.bat`
- `20_build_dist.bat`
- `30_build_installer.bat`
- `99_release_all.bat`

Validar que los artefactos generados (dist/instalador) correspondan a la versión etiquetada y se puedan instalar/ejecutar correctamente.
