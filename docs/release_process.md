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
- Calidad mínima: ejecutar `python -m scripts.quality_gate` (lee el umbral desde `.config/quality_gate.json`).

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


## 6) Build reproducible en Windows desde GitHub Actions

Existe un workflow dedicado en `.github/workflows/release_build_windows.yml` que genera un build de Windows con PyInstaller usando `packaging/HorasSindicales.spec`.

Pasos principales del job `build_windows`:

- Instala dependencias (`requirements.txt` y `requirements-dev.txt`).
- Verifica sintaxis (`compileall`) y ejecuta smoke mínimo (`python -c "import app"`).
- Ejecuta `pyinstaller packaging/HorasSindicales.spec --noconfirm` y guarda logs en:
  - `logs/build_stdout.log`
  - `logs/build_stderr.log`
- Lee la versión desde `VERSION` y empaqueta `dist/HorasSindicales` en:
  - `HorasSindicales-v{VERSION}-windows.zip`
- Publica como artifact el ZIP y los logs.

### Descargar artifact desde Actions

1. Ir a la pestaña **Actions** del repositorio.
2. Abrir el workflow **Release Build Windows**.
3. Seleccionar una ejecución completada.
4. En la sección **Artifacts**, descargar `HorasSindicales-vX.Y.Z-windows`.

### Ejecutar en Windows

1. Descomprimir `HorasSindicales-vX.Y.Z-windows.zip`.
2. Entrar a la carpeta extraída.
3. Ejecutar `HorasSindicales.exe`.
