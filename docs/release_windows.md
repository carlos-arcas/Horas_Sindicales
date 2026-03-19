# Release Windows

Guía operativa mínima para generar y revisar el build Windows de **Horas Sindicales** sin apoyarse en scripts históricos.

## Artefactos reales del flujo

- PyInstaller: `packaging/HorasSindicales.spec`
- Instalador Inno Setup: `installer/HorasSindicales.iss`
- Workflow oficial: `.github/workflows/release_build_windows.yml`

## Preparación local

En una máquina Windows con Python disponible:

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

## Comprobación previa obligatoria

Antes de compilar, ejecuta:

```powershell
python -m scripts.gate_pr
```

Si el gate no pasa, no tiene sentido generar un build de distribución.

## Qué hace el workflow oficial

El job `build_windows` realiza este contrato:

1. `python -m compileall -q app scripts`
2. `python -c "import app"`
3. `pyinstaller packaging/HorasSindicales.spec --noconfirm`
4. lectura de `VERSION`
5. creación de `HorasSindicales-v{VERSION}-windows.zip`
6. generación de `HorasSindicales-v{VERSION}-windows.sha256`

## Ejecución manual equivalente

Si necesitas reproducirlo localmente:

```powershell
python -m compileall -q app scripts
python -c "import app"
pyinstaller packaging/HorasSindicales.spec --noconfirm
```

Después empaqueta manualmente la carpeta `dist/HorasSindicales` y calcula un SHA256 del ZIP final.

## Validación mínima del resultado

En una máquina Windows real:

- abrir la aplicación;
- comprobar que arranca la ventana principal;
- validar un flujo core representativo;
- revisar que se crean logs operativos;
- confirmar que el ZIP distribuido coincide con la versión etiquetada.

## Evidencia útil

Conserva al menos:

- `logs/build_stdout.log`;
- `logs/build_stderr.log`;
- ZIP distribuido;
- SHA256;
- referencia al run de GitHub Actions que generó el artefacto.

## Qué evitar

- Documentar scripts de build que ya no existen.
- Publicar un ZIP sin haber pasado `python -m scripts.gate_pr`.
- Dar por bueno el build sin validación manual en Windows real.
