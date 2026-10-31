# PyInstaller spec for Griffin Updater.
# Build with: pyinstaller packaging/griffin-updater.spec --noconfirm
import os

block_cipher = None

a = Analysis(
    ["run_griffin_updater.py"],
    pathex=[os.path.abspath(os.path.join(SPECPATH, ".."))],
    binaries=[],
    datas=[(os.path.join(SPECPATH, "..", "resources", "griffin-updater.png"), "resources")],
    hiddenimports=[
        "PyQt6.QtCore",
        "PyQt6.QtGui",
        "PyQt6.QtWidgets",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="griffin-updater",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="griffin-updater",
)
