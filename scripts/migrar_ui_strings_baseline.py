from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from pathlib import Path

BASELINE_PATH = Path('.config/ui_strings_baseline.json')
OUT_DIR = Path('configuracion/i18n')
OUT_ES_PATH = OUT_DIR / 'es.json'
OUT_LEGACY_MAP_PATH = OUT_DIR / '_legacy_map.json'
PATRON_LEGACY = re.compile(r'^(?P<ruta>.+):(?P<linea>\d+):(?P<texto>.+)$')


def _slug_texto(texto: str) -> str:
    normalizado = unicodedata.normalize('NFKD', texto.lower())
    sin_tildes = ''.join(ch for ch in normalizado if not unicodedata.combining(ch))
    slug = re.sub(r'[^a-z0-9]+', '_', sin_tildes).strip('_')
    return (slug or 'texto')[:40]


def _hash_texto(texto: str, size: int = 8) -> str:
    return hashlib.sha1(texto.encode('utf-8')).hexdigest()[:size]


def _key_base(ruta: str, texto: str) -> str:
    path = Path(ruta)
    modulo = path.parts[0] if path.parts else 'ui'
    archivo = path.stem
    return f'ui.{modulo}.{archivo}.{_slug_texto(texto)}'


def _key_estable(ruta: str, texto: str, usadas: dict[str, str]) -> str:
    base = _key_base(ruta, texto)
    hash_actual = _hash_texto(texto)
    candidata = f'{base}_{hash_actual}'
    if candidata not in usadas or usadas[candidata] == texto:
        usadas[candidata] = texto
        return candidata

    extra = 1
    while True:
        hash_colision = _hash_texto(f'{texto}::{extra}')
        alternativa = f'{base}_{hash_colision}'
        if alternativa not in usadas or usadas[alternativa] == texto:
            usadas[alternativa] = texto
            return alternativa
        extra += 1


def migrar() -> None:
    payload = json.loads(BASELINE_PATH.read_text(encoding='utf-8'))
    offenders = sorted(set(payload.get('offenders', [])))

    legacy_map: dict[str, str] = {}
    es_catalogo: dict[str, str] = {}
    usadas: dict[str, str] = {}

    for legacy in offenders:
        match = PATRON_LEGACY.match(legacy)
        if not match:
            continue
        ruta = match.group('ruta')
        texto = match.group('texto')
        key = _key_estable(ruta, texto, usadas)
        legacy_map[legacy] = key
        es_catalogo.setdefault(key, texto)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_ES_PATH.write_text(
        json.dumps(dict(sorted(es_catalogo.items())), ensure_ascii=False, indent=2) + '\n',
        encoding='utf-8',
    )
    OUT_LEGACY_MAP_PATH.write_text(
        json.dumps(dict(sorted(legacy_map.items())), ensure_ascii=False, indent=2) + '\n',
        encoding='utf-8',
    )


if __name__ == '__main__':
    migrar()
