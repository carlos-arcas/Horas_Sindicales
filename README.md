# Horas Sindicales

Aplicación de escritorio (PySide6) para la gestión de **horas sindicales**, incluyendo:

- Alta y mantenimiento de personas.
- Registro de solicitudes de horas (por tramo o jornada completa).
- Generación de PDF de solicitudes.
- Persistencia local en SQLite con migraciones automáticas.
- Sincronización bidireccional con Google Sheets y resolución de discrepancias.

## Requisitos técnicos

- **Python 3.10 o superior** (recomendado: 3.12).
- Sistema operativo: Windows/Linux/macOS.
- Dependencias Python (ver `requirements.txt`):
  - `PySide6`
  - `reportlab`
  - `gspread`
  - `google-auth`
  - `google-auth-oauthlib`
  - `google-api-python-client`
  - `python-dotenv`

> Nota: Para usar la sincronización con Google Sheets necesitas credenciales válidas (archivo JSON de servicio/OAuth según configuración de la organización).

## Instalación

1. Clona el repositorio:

   ```bash
   git clone <URL_DEL_REPOSITORIO>
   cd Horas_Sindicales
   ```

2. Crea y activa un entorno virtual:

   **Linux/macOS**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

   **Windows (PowerShell)**
   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. Instala dependencias:

   ```bash
   pip install -U pip
   pip install -r requirements.txt
   ```

## Ejecución

### Modo normal

```bash
python main.py
```

### Self-check (sin abrir UI)

Valida recursos estáticos básicos (por ejemplo, hoja de estilos e imágenes):

```bash
python main.py --selfcheck
```

### Lanzador Windows

También puedes usar:

```bat
launch.bat
```

Este script crea `.venv`, instala dependencias y ejecuta la app.

## Estructura del proyecto

```text
.
├── app/
│   ├── application/      # Casos de uso y servicios de aplicación
│   ├── domain/           # Entidades, reglas de negocio y puertos
│   ├── infrastructure/   # SQLite, migraciones, repositorios y adaptadores externos
│   ├── pdf/              # Construcción y servicio de generación de PDF
│   └── ui/               # Ventanas, diálogos, widgets y estilos Qt
├── tests/                # Pruebas automatizadas (pytest)
├── main.py               # Punto de entrada
├── requirements.txt      # Dependencias
└── launch.bat            # Arranque asistido en Windows
```

## Tests

Ejecuta la suite con `pytest`:

```bash
PYTHONPATH=. pytest -q
```

## Arquitectura (resumen por capas)

El proyecto sigue una separación por capas con responsabilidades claras:

- **Domain**: modelos de negocio, reglas y contratos (puertos).
- **Application**: orquestación de casos de uso y servicios que coordinan dominio e infraestructura.
- **Infrastructure**: implementación técnica (SQLite, Google Sheets, configuración local, migraciones).
- **UI**: capa de presentación en PySide6 que consume casos de uso.

Esta organización facilita evolución, testeo y reemplazo de integraciones externas con impacto mínimo en el núcleo funcional.

## Licencia

Pendiente de definir. Se recomienda añadir un archivo `LICENSE` (por ejemplo, MIT, Apache-2.0 o licencia interna corporativa).
