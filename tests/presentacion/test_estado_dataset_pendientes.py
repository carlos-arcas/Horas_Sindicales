from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

from app.application.dto import SolicitudDTO



def _load_estado_dataset_module():
    module_path = Path("app/ui/vistas/main_window/estado_dataset_pendientes.py")
    spec = spec_from_file_location("estado_dataset_pendientes_local", module_path)
    assert spec is not None and spec.loader is not None
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _solicitud(solicitud_id: int, persona_id: int) -> SolicitudDTO:
    return SolicitudDTO(
        id=solicitud_id,
        persona_id=persona_id,
        fecha_solicitud="2026-03-01",
        fecha_pedida="2026-03-01",
        desde="09:00",
        hasta="10:00",
        completo=False,
        horas=1.0,
        observaciones="",
        notas="",
        pdf_path=None,
        pdf_hash=None,
    )


def test_calcular_dataset_ver_todas_no_deja_ocultas() -> None:
    modulo = _load_estado_dataset_module()
    pendientes_totales = [_solicitud(1, 10), _solicitud(2, 20)]

    estado = modulo.calcular_estado_dataset_pendientes(
        pendientes_totales=pendientes_totales,
        delegada_activa_id=10,
        ver_todas_delegadas=True,
    )

    assert [s.id for s in estado.pendientes_visibles] == [1, 2]
    assert estado.pendientes_ocultas == []
    assert estado.pendientes_otras_delegadas == []
    assert estado.motivos_exclusion == {}


def test_calcular_dataset_modo_normal_separa_ocultas_y_motivos() -> None:
    modulo = _load_estado_dataset_module()
    pendientes_totales = [_solicitud(1, 10), _solicitud(2, 20), _solicitud(3, 20)]

    estado = modulo.calcular_estado_dataset_pendientes(
        pendientes_totales=pendientes_totales,
        delegada_activa_id=10,
        ver_todas_delegadas=False,
    )

    assert [s.id for s in estado.pendientes_visibles] == [1]
    assert [s.id for s in estado.pendientes_ocultas] == [2, 3]
    assert [s.id for s in estado.pendientes_otras_delegadas] == [2, 3]
    assert estado.motivos_exclusion == {
        2: modulo.MOTIVO_EXCLUSION_DELEGADA_DISTINTA,
        3: modulo.MOTIVO_EXCLUSION_DELEGADA_DISTINTA,
    }
