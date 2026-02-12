# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

project_root = Path.cwd()


def _existing(*relative_paths: str) -> list[tuple[str, str]]:
    entries: list[tuple[str, str]] = []
    for rel in relative_paths:
        src = project_root / rel
        if src.exists():
            dst = str(Path(rel).parent).replace('\\', '/')
            if dst == '.':
                dst = '.'
            entries.append((str(src), dst))
    return entries


def _existing_glob(pattern: str, destination: str) -> list[tuple[str, str]]:
    entries: list[tuple[str, str]] = []
    for src in sorted(project_root.glob(pattern)):
        if src.is_file():
            entries.append((str(src), destination))
    return entries


datas = []
datas += _existing(
    'app/ui/styles/cgt_dark.qss',
    'logo.png',
    'cgt_reservar_horas_sindicales.ico',
)
datas += _existing_glob('migrations/*.sql', 'migrations')
datas += _existing_glob('migrations/*.py', 'migrations')

hiddenimports = [
    'PySide6.QtPdf',
    'PySide6.QtPdfWidgets',
    'googleapiclient.discovery',
    'googleapiclient.http',
]
hiddenimports += collect_submodules('gspread')

block_cipher = None


a = Analysis(
    ['main.py'],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='HorasSindicales',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(project_root / 'cgt_reservar_horas_sindicales.ico') if (project_root / 'cgt_reservar_horas_sindicales.ico').exists() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='HorasSindicales',
)
