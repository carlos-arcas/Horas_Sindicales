from __future__ import annotations

from app.application.dto import SolicitudDTO
from app.application.use_cases.solicitudes.helpers_puros import (
    mensaje_conflicto,
    mensaje_duplicado,
    mensaje_persona_invalida,
    mensaje_warning_saldo_insuficiente,
    normalizar_dto_para_creacion,
    resultado_error_creacion,
    saldo_insuficiente,
)


def _dto_base() -> SolicitudDTO:
    return SolicitudDTO(
        id=None,
        persona_id=1,
        fecha_solicitud="1/2/2025",
        fecha_pedida="2/2/2025",
        desde="9:00",
        hasta="11:30",
        completo=False,
        horas=2.5,
        observaciones="Obs",
        pdf_path=None,
        pdf_hash=None,
        notas="N",
    )


def test_resultado_error_creacion_retorna_dto_fallido() -> None:
    resultado = resultado_error_creacion(errores=["x"], warnings=["w"])

    assert resultado.success is False
    assert resultado.entidad is None
    assert resultado.errores == ["x"]
    assert resultado.warnings == ["w"]


def test_mensaje_persona_invalida_para_id_cero() -> None:
    assert mensaje_persona_invalida(0) == "Selecciona una delegada válida antes de guardar la solicitud."


def test_mensaje_persona_invalida_para_id_negativo() -> None:
    assert mensaje_persona_invalida(-10) == "Selecciona una delegada válida antes de guardar la solicitud."


def test_mensaje_persona_invalida_para_id_valido_devuelve_none() -> None:
    assert mensaje_persona_invalida(5) is None


def test_normalizar_dto_para_creacion_normaliza_fecha_y_horas() -> None:
    dto = normalizar_dto_para_creacion(_dto_base())

    assert dto.fecha_pedida == "2025-02-02"
    assert dto.fecha_solicitud == "2025-02-01"
    assert dto.desde == "09:00"
    assert dto.hasta == "11:30"


def test_normalizar_dto_para_creacion_respeta_none_en_rangos() -> None:
    dto_sin_rangos = _dto_base()
    dto_sin_rangos = SolicitudDTO(**{**dto_sin_rangos.__dict__, "desde": None, "hasta": None, "completo": True, "horas": 4.0})

    dto = normalizar_dto_para_creacion(dto_sin_rangos)

    assert dto.desde is None
    assert dto.hasta is None


def test_mensaje_conflicto_con_accion() -> None:
    assert mensaje_conflicto("SUSTITUIR") == "Conflicto completo/parcial en la misma fecha. Acción sugerida: SUSTITUIR."


def test_mensaje_conflicto_con_accion_none() -> None:
    assert mensaje_conflicto(None).endswith("None.")


def test_mensaje_duplicado_confirmado() -> None:
    assert mensaje_duplicado(True) == "Duplicado confirmado"


def test_mensaje_duplicado_pendiente() -> None:
    assert mensaje_duplicado(False) == "Duplicado pendiente"


def test_saldo_insuficiente_cuando_mes_no_alcanza() -> None:
    assert saldo_insuficiente(restantes_mes=10, restantes_ano=500, minutos_solicitados=30) is True


def test_saldo_insuficiente_cuando_ano_no_alcanza() -> None:
    assert saldo_insuficiente(restantes_mes=500, restantes_ano=20, minutos_solicitados=30) is True


def test_saldo_insuficiente_false_en_borde_igual() -> None:
    assert saldo_insuficiente(restantes_mes=30, restantes_ano=30, minutos_solicitados=30) is False


def test_mensaje_warning_saldo_insuficiente() -> None:
    assert mensaje_warning_saldo_insuficiente() == "Saldo insuficiente. La petición se ha registrado igualmente."

