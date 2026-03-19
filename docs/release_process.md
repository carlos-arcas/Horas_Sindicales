# Proceso de release

Esta guía resume el flujo real de publicación del repositorio sin inventar pasos ni scripts que ya no existen.
El producto sigue siendo una **aplicación de escritorio Python + PySide6** y la validación previa a release debe pasar por el gate oficial.

## 1. Preparar versión

Antes de etiquetar una release:

1. Actualiza `VERSION` con formato `MAJOR.MINOR.PATCH`.
2. Revisa `CHANGELOG.md` y mueve los cambios desde `Unreleased` a la versión nueva.
3. Verifica que el estado del producto siga alineado con `docs/definicion_producto_final.md`.

## 2. Validación obligatoria

Ejecuta primero el gate completo:

```bash
python -m scripts.gate_pr
```

Después, si quieres una verificación de release con árbol limpio y changelog/versionado consistentes:

```bash
make release-check
```

Ese comando ejecuta `scripts/release/release.py` y comprueba:

- árbol git limpio;
- versión SemVer válida en `app/__init__.py`;
- entrada correspondiente en `CHANGELOG.md`.

## 3. Build Windows reproducible

El build oficial de distribución vive en GitHub Actions:

- workflow: `.github/workflows/release_build_windows.yml`;
- empaquetado: `packaging/HorasSindicales.spec`;
- instalador: `installer/HorasSindicales.iss`.

El workflow:

1. instala dependencias;
2. valida sintaxis e import básico de `app`;
3. genera el build con PyInstaller;
4. empaqueta el resultado en un ZIP versionado;
5. publica ZIP, checksum y logs como artefactos.

## 4. Etiquetado

Cuando el gate y la validación de release pasen:

```bash
git tag vX.Y.Z
git push --tags
```

Después crea la release en GitHub usando las notas de `CHANGELOG.md`.

## 5. Evidencia que conviene conservar

- salida de `python -m scripts.gate_pr`;
- artefactos del workflow `Release Build Windows`;
- checksum SHA256 del ZIP distribuido;
- versión publicada en `VERSION` y `CHANGELOG.md`.

## 6. Lo que ya no forma parte del flujo activo

No dependas de scripts históricos de release fuera de los entrypoints actuales del repo.
Si reaparece documentación que mencione launchers o pipelines ya eliminados, hay que corregirla antes de publicar.
