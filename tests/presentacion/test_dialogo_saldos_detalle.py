from __future__ import annotations

from app.ui.dialogos.dialogo_saldos_detalle import copiar_estado_saldos


class EtiquetaFalsa:
    def __init__(self, texto: str = "", visible: bool = True) -> None:
        self._texto = texto
        self._visible = visible

    def text(self) -> str:
        return self._texto

    def setText(self, valor: str) -> None:
        self._texto = valor

    def isVisible(self) -> bool:
        return self._visible

    def setVisible(self, valor: bool) -> None:
        self._visible = valor


class SaldosCardFalsa:
    def __init__(self) -> None:
        self.saldo_periodo_label = EtiquetaFalsa()
        self.saldo_periodo_consumidas = EtiquetaFalsa()
        self.saldo_periodo_restantes = EtiquetaFalsa()
        self.saldo_anual_consumidas = EtiquetaFalsa()
        self.saldo_anual_restantes = EtiquetaFalsa()
        self.saldo_grupo_consumidas = EtiquetaFalsa()
        self.saldo_grupo_restantes = EtiquetaFalsa()
        self.bolsa_mensual_label = EtiquetaFalsa()
        self.bolsa_delegada_label = EtiquetaFalsa()
        self.bolsa_grupo_label = EtiquetaFalsa()
        self.exceso_badge = EtiquetaFalsa()

    def update_periodo_label(self, valor: str) -> None:
        self.saldo_periodo_label.setText(valor)


def test_copiar_estado_saldos_transfiere_textos_y_visibilidad() -> None:
    origen = SaldosCardFalsa()
    origen.update_periodo_label("Mensual (06/2026)")
    origen.saldo_periodo_consumidas.setText("30")
    origen.saldo_periodo_restantes.setText("270")
    origen.saldo_anual_consumidas.setText("100")
    origen.saldo_anual_restantes.setText("3900")
    origen.saldo_grupo_consumidas.setText("120")
    origen.saldo_grupo_restantes.setText("3880")
    origen.bolsa_mensual_label.setText("Bolsa mensual: 300")
    origen.bolsa_delegada_label.setText("Bolsa delegada: 4000")
    origen.bolsa_grupo_label.setText("Bolsa grupo: 4000")
    origen.exceso_badge.setVisible(True)
    origen.exceso_badge.setText("Exceso detectado")

    destino = SaldosCardFalsa()

    copiar_estado_saldos(origen, destino)

    assert destino.saldo_periodo_label.text() == "Mensual (06/2026)"
    assert destino.saldo_periodo_consumidas.text() == "30"
    assert destino.saldo_periodo_restantes.text() == "270"
    assert destino.saldo_anual_consumidas.text() == "100"
    assert destino.saldo_anual_restantes.text() == "3900"
    assert destino.saldo_grupo_consumidas.text() == "120"
    assert destino.saldo_grupo_restantes.text() == "3880"
    assert destino.bolsa_mensual_label.text() == "Bolsa mensual: 300"
    assert destino.bolsa_delegada_label.text() == "Bolsa delegada: 4000"
    assert destino.bolsa_grupo_label.text() == "Bolsa grupo: 4000"
    assert destino.exceso_badge.isVisible() is True
    assert destino.exceso_badge.text() == "Exceso detectado"
