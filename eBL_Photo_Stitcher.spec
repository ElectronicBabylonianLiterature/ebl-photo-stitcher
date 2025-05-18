# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for eBL Photo Stitcher.
This builds a single executable with all required dependencies.
"""

block_cipher = None

a = Analysis(
    ['gui_app.py'],
    pathex=['./lib'],
    binaries=[],
    datas=[
        ('assets', 'assets'),
    ],
    hiddenimports=[
        'cv2', 
        'numpy',
        'imageio',
        'rawpy',
        'piexif',
        'pyexiv2',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

excluded_binaries = [
    'opengl32sw.dll',
    'VCRUNTIME140.dll',
    'MSVCP140.dll',
    'api-ms-win-core*.dll',
    'api-ms-win-crt*.dll',
    'opencv_videoio_ffmpeg*.dll',
    'libopenblas*.dll',
]

a.binaries = TOC([x for x in a.binaries if not any(
    excluded in x[0] for excluded in excluded_binaries)])

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='eBL Photo Stitcher',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='eBL_Logo.ico',
)
