# -*- mode: python ; coding: utf-8 -*-
#
# CI-Hörtrainer – PyInstaller Build Specification
# Build command: pyinstaller ci_trainer.spec
#

import sys
import pathlib

block_cipher = None
ROOT = pathlib.Path(SPECPATH)  # project root

# ── Collect all data files that must be bundled ──────────────────────────────
added_datas = [
    # Static web UI (HTML, CSS, JS, assets)
    (str(ROOT / "src" / "web" / "static"), "src/web/static"),
    # Audio data (noise files, test audio)
    (str(ROOT / "data"),                   "data"),
    # Speech recognition / Whisper models (may be empty on first run)
    (str(ROOT / "models"),                 "models"),
]

# ── Hidden imports that PyInstaller may miss ─────────────────────────────────
hidden_imports = [
    # Standard library modules used dynamically
    "http.server",
    "socketserver",
    "webbrowser",
    "threading",
    "atexit",
    "signal",
    # Our source packages
    "src.web.server",
    "src.audio.tts_engine",
    "src.audio.player",
    "src.audio.olsa_adaptive",
    "src.audio.ci_vocoder",
    "src.database.progress_db",
    "src.evaluator.phonetic_matcher",
    "src.stt.stt_engine",
    # Third-party
    "edge_tts",
    "speech_recognition",
]

a = Analysis(
    ["main.py"],
    pathex=[str(ROOT)],
    binaries=[],
    datas=added_datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude heavy unused packages to keep bundle lean
        "matplotlib", "numpy", "pandas", "PIL", "tkinter",
        "IPython", "jupyter", "notebook",
        "pytest", "unittest",
    ],
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
    name="CI-Hörtrainer",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,              # UPX disabled: avoids ARM64 issues on macOS
    console=False,          # No terminal window on Windows/Linux
    disable_windowed_traceback=False,
    argv_emulation=False,   # Disabled: prevents silent exit on macOS LaunchServices / ARM64
    target_arch=None,
    codesign_identity=None, # No code signing – user signs manually if needed
    entitlements_file=None,
    # Windows: embed icon
    icon="docs/iconset/icon.ico" if (ROOT / "docs/iconset/icon.ico").exists() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="CI-Hörtrainer",
)

# ── macOS: wrap in .app bundle ───────────────────────────────────────────────
if sys.platform == "darwin":
    app = BUNDLE(
        coll,
        name="CI-Hörtrainer.app",
        icon="docs/iconset/icon.icns" if (ROOT / "docs/iconset/icon.icns").exists() else None,
        bundle_identifier="de.ci-hoertrainer.app",
        info_plist={
            "CFBundleShortVersionString": "1.0.0",
            "CFBundleVersion": "1.0.0",
            "NSHighResolutionCapable": True,
            "LSBackgroundOnly": False,
            "CFBundleDisplayName": "CI-Hörtrainer",
            "NSHumanReadableCopyright": "© 2026 CI-Hörtrainer",
        },
    )
