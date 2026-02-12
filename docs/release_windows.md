# Release Windows (PySide6 + PyInstaller + Inno Setup)

Esta guía automatiza la generación del ejecutable distribuible y del instalador `.exe` para usuarios no técnicos.

## 1) Prerrequisitos en Windows

Antes de ejecutar los scripts, instala:

1. **Python 3.x para Windows**
   - Verifica con: `py -V`
   - Recomendado marcar la opción de agregar Python al PATH durante la instalación.
2. **Inno Setup 6**
   - Verifica compilador con: `ISCC.exe` en PATH, o en una de estas rutas:
     - `C:\Program Files (x86)\Inno Setup 6\ISCC.exe`
     - `C:\Program Files\Inno Setup 6\ISCC.exe`

## 2) Archivos requeridos del proyecto

Asegúrate de tener estos archivos de texto en el repo:

- `packaging/HorasSindicales.spec` (PyInstaller)
- `installer/HorasSindicales.iss` (Inno Setup)

> Los scripts validan estas rutas antes de compilar.

## 3) Scripts de automatización y cuándo usar cada uno

Todos los scripts están en `scripts/release/`.

### Flujo completo (primera vez o release completo)

Ejecuta:

```bat
scripts\release\99_release_all.bat
```

Este maestro corre en orden:

1. `00_check_prereqs.bat`
2. `10_setup_venv.bat`
3. `20_build_dist.bat`
4. `30_build_installer.bat`

### Solo recompilar instalador (si `dist/` ya existe)

```bat
scripts\release\30_build_installer.bat
```

Útil cuando cambias solo parámetros del `.iss` (icono, metadatos, acceso directo, nombre del setup, etc.).

### Si cambian dependencias Python

```bat
scripts\release\10_setup_venv.bat
```

Recrea/actualiza el entorno `.venv`, actualiza pip e instala dependencias.

## 4) Archivo final a entregar

El objetivo de distribución es el instalador:

- **`HorasSindicalesSetup.exe`**

El script `30_build_installer.bat` intenta localizar automáticamente el resultado en:

- `output\*.exe`
- `installer\output\*.exe`
- y rutas típicas de fallback.

## 5) Checklist de validación en PC limpio

Antes de entregar, prueba en un equipo sin entorno de desarrollo:

- [ ] Instalar ejecutando `HorasSindicalesSetup.exe`.
- [ ] Abrir la app desde acceso directo de escritorio o menú inicio.
- [ ] Confirmar que la ventana principal carga sin errores.
- [ ] Probar flujo crítico de negocio (crear/editar solicitud, guardar, etc.).
- [ ] Verificar que PDF/exports (si aplica) se generan bien.
- [ ] Cerrar y reabrir para validar persistencia/configuración.
- [ ] Desinstalar y confirmar limpieza esperada.

## 6) Problemas típicos y logs

## Problema: faltan plugins de Qt/PySide6

Síntomas frecuentes:

- Error al abrir app relacionado con `Qt platform plugin` (por ejemplo `windows` no encontrado).
- La app no inicia en equipos sin entorno Python.

Qué revisar:

1. Configuración de `packaging/HorasSindicales.spec`:
   - `hiddenimports`
   - `datas`
   - colecciones de plugins Qt necesarias.
2. Salida de `20_build_dist.bat` y logs de PyInstaller.
3. Estructura generada dentro de `dist/` (carpetas de Qt/plugins).

## Problema: falla ISCC al compilar

El script `30_build_installer.bat` interpreta códigos de salida de ISCC:

- `0`: correcto
- `1`: parámetros inválidos o error interno
- `2`: fallo de compilación del instalador

Qué revisar:

- Sintaxis y rutas dentro de `installer/HorasSindicales.iss`.
- Que `dist/` exista y contenga la app compilada.
- Permisos de escritura en carpeta de salida (`OutputDir`).

## Problema: no aparece el setup final

Si ISCC termina sin error pero no localizas el `.exe`:

- Revisa `OutputDir` y `OutputBaseFilename` en `installer/HorasSindicales.iss`.
- Busca manualmente en la carpeta configurada.
- Vuelve a correr `30_build_installer.bat` para mostrar la ruta detectada.
