# -*- mode: python ; coding: utf-8 -*-
# Spécification PyInstaller pour la version macOS de DOSOFT (bundle .app).
# Utilisation : ./build_mac.sh   (ou : pyinstaller --noconfirm Dosoft-mac.spec)
import json
import os
from PyInstaller.utils.hooks import collect_all

with open("version.json", encoding="utf-8") as f:
    APP_VERSION = json.load(f).get("version", "0.0.0")

ICON = os.environ.get("DOSOFT_ICNS", "build/mac/Dosoft.icns")

datas = [
    ("skin", "skin"),
    ("sounds", "sounds"),
    ("resources/i18n", "resources/i18n"),
    ("resources/keyboards", "resources/keyboards"),
    ("logo.ico", "."),
    ("version.json", "."),
]
binaries = []
hiddenimports = [
    "platform_backend.macos", "platform_backend.mac_keycodes", "platform_backend.mac_notifications",
    "customtkinter", "PIL", "PIL.ImageTk", "pygame",
    "objc", "Quartz", "AppKit", "Foundation", "ApplicationServices",
]
tmp_ret = collect_all("customtkinter")
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "platform_backend.windows", "win32api", "win32con", "win32gui", "win32process",
        "pythoncom", "winrt", "keyboard", "pystray",
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Dosoft",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=os.environ.get("DOSOFT_TARGET_ARCH") or None,
    codesign_identity=os.environ.get("DOSOFT_CODESIGN_IDENTITY") or None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="Dosoft",
)

app = BUNDLE(
    coll,
    name="Dosoft.app",
    icon=ICON if os.path.exists(ICON) else None,
    bundle_identifier="fr.dosoft.app",
    version=APP_VERSION,
    info_plist={
        "CFBundleName": "Dosoft",
        "CFBundleDisplayName": "DOSOFT",
        "CFBundleShortVersionString": APP_VERSION,
        "CFBundleVersion": APP_VERSION,
        "LSMinimumSystemVersion": "11.0",
        "NSHighResolutionCapable": True,
        "LSApplicationCategoryType": "public.app-category.utilities",
        "NSHumanReadableCopyright": "DOSOFT - https://dosoft.fr",
        "NSAppleEventsUsageDescription": "DOSOFT pilote les fenêtres Dofus (mise au premier plan).",
    },
)
