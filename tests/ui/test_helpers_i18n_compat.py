from __future__ import annotations

from app.ui.vistas.helpers_i18n_compat import resolver_texto_i18n


class _Gestor:
    def t(self, key: str, *, fallback: str | None = None, **params: object) -> str:
        if key == "ok":
            return "Texto OK"
        return fallback or ""


def test_resolver_texto_i18n_prioriza_gestor() -> None:
    texto = resolver_texto_i18n(i18n=_Gestor(), key="ok", fallback="fallback", catalogo={})

    assert texto == "Texto OK"


def test_resolver_texto_i18n_usa_catalogo_si_no_hay_gestor() -> None:
    texto = resolver_texto_i18n(
        i18n=None,
        key="clave",
        fallback="fallback",
        catalogo={"es": {"clave": "Desde catálogo"}},
    )

    assert texto == "Desde catálogo"
