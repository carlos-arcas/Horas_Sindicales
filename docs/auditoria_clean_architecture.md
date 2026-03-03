# Auditoría de Clean Architecture

- Violaciones de dependencias: **2**
- Indicios de negocio en UI: **5**

## Violaciones de imports entre capas
| Tipo | Archivo | Línea | Origen | Destino |
|---|---|---:|---|---|
| ui_importa_infraestructura | `presentacion/i18n/__init__.py` | 13 | `presentacion.i18n.__init__` | `infraestructura.i18n.proveedor_traducciones` |
| ui_importa_infraestructura | `presentacion/i18n/catalogo.py` | 3 | `presentacion.i18n.catalogo` | `infraestructura.i18n.proveedor_traducciones` |

## Indicios de negocio en UI
| Tipo | Archivo | Línea | Detalle |
|---|---|---:|---|
| ui_importa_acceso_datos | `app/ui/i18n_interfaz.py` | 6 | aplicacion.puertos.proveedor_i18n |
| ui_importa_acceso_datos | `app/ui/vistas/main_window/state_controller.py` | 151 | aplicacion.puertos.proveedor_i18n |
| ui_importa_acceso_datos | `presentacion/i18n/__init__.py` | 13 | infraestructura.i18n.proveedor_traducciones |
| ui_importa_acceso_datos | `presentacion/i18n/catalogo.py` | 3 | infraestructura.i18n.proveedor_traducciones |
| ui_importa_acceso_datos | `presentacion/i18n/gestor_i18n.py` | 11 | aplicacion.puertos.proveedor_i18n |
