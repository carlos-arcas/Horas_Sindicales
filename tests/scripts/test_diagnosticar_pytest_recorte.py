from __future__ import annotations

from scripts.diagnosticar_pytest import recortar_head_tail


def test_recortar_head_tail_con_texto_largo() -> None:
    texto = "\n".join(f"linea-{indice}" for indice in range(500))

    resultado = recortar_head_tail(texto, head=3, tail=4)

    assert len(resultado["head"]) == 3
    assert len(resultado["tail"]) == 4
    assert resultado["head"] == ["linea-0", "linea-1", "linea-2"]
    assert resultado["tail"] == ["linea-496", "linea-497", "linea-498", "linea-499"]
