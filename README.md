# Horas Sindicales

Aplicación de escritorio (PySide6) para gestionar horas sindicales:
- gestión de personas delegadas,
- registro de solicitudes (parcial o completa),
- generación de PDFs,
- persistencia local en SQLite,
- sincronización bidireccional con Google Sheets.

## Documentación
- Arquitectura: [arquitectura.md](./arquitectura.md)
- Onboarding: [docs/onboarding.md](./docs/onboarding.md)
- Reglas de negocio: [docs/reglas_negocio.md](./docs/reglas_negocio.md)
- Sincronización técnica: [docs/sincronizacion_google_sheets.md](./docs/sincronizacion_google_sheets.md)
- Decisiones (ADR): [docs/decisiones.md](./docs/decisiones.md)

## Requisitos
- Python 3.10+ (recomendado 3.12).
- Windows/Linux/macOS.
- Dependencias en `requirements.txt`.

Para sincronización con Google Sheets necesitas credenciales válidas.

## Instalación
1. Clonar repositorio:
   ```bash
   git clone <URL_DEL_REPOSITORIO>
   cd Horas_Sindicales
   ```
2. Crear entorno virtual.
   - Linux/macOS:
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```powershell
     py -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```
3. Instalar dependencias:
   ```bash
   pip install -U pip
   pip install -r requirements.txt
   ```

## Ejecución
- App:
  ```bash
  python main.py
  ```
- Self-check (sin abrir UI):
  ```bash
  python main.py --selfcheck
  ```
- Windows: `launch.bat` (crea `.venv`, instala dependencias y arranca).

## Estructura
```text
app/
  application/    Casos de uso y orquestación
  domain/         Modelo y reglas de negocio
  infrastructure/ SQLite, migraciones, repositorios, adaptadores externos
  pdf/            Generación de PDF
  ui/             Interfaz PySide6
tests/            Suite pytest
main.py           Entry point
```

## Tests
```bash
PYTHONPATH=. pytest -q
```

## Licencia
Pendiente de definir (`LICENSE`).
