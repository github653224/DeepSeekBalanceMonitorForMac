# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules


ROOT = Path.cwd()
SRC = ROOT / "src"
PACKAGE = SRC / "deepseek_balance_monitor_mac"
ASSETS = PACKAGE / "assets"


datas = [
    (str(ASSETS / "AppIcon.png"), "assets"),
    (str(ASSETS / "AppIcon.icns"), "assets"),
    (str(ASSETS / "font" / "ShareTech-Regular.ttf"), "assets/font"),
]

hiddenimports = [
    "deepseek_balance_monitor_mac",
    "deepseek_balance_monitor_mac.api_client",
    "deepseek_balance_monitor_mac.app_state",
    "deepseek_balance_monitor_mac.config",
    "deepseek_balance_monitor_mac.credential_store",
    "deepseek_balance_monitor_mac.history_dialog",
    "deepseek_balance_monitor_mac.icon_renderer",
    "deepseek_balance_monitor_mac.secure_settings",
    "deepseek_balance_monitor_mac.storage",
    "deepseek_balance_monitor_mac.core.monitoring",
    "deepseek_balance_monitor_mac.infra.exchange_rates",
    "deepseek_balance_monitor_mac.infra.secret_store",
    "deepseek_balance_monitor_mac.mac.keystore",
    "deepseek_balance_monitor_mac.mac.settings",
]
hiddenimports += collect_submodules("rumps")

excludes = [
    "pystray",
    "pywebview",
    "tkhtmlview",
    "matplotlib",
    "numpy",
    "pandas",
    "pytest",
]


a = Analysis(
    [str(PACKAGE / "mac" / "main.py")],
    pathex=[str(ROOT), str(SRC)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="DeepSeek Balance Monitor",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    argv_emulation=False,
)

app = BUNDLE(
    exe,
    a.binaries,
    a.datas,
    name="DeepSeek Balance Monitor.app",
    icon=str(ASSETS / "AppIcon.icns"),
    bundle_identifier="com.deepseek.balance.monitor",
    info_plist={
        "CFBundleName": "DeepSeek Balance Monitor",
        "CFBundleDisplayName": "DeepSeek Balance Monitor",
        "CFBundleShortVersionString": "0.1.0",
        "CFBundleVersion": "0.1.0",
        "LSUIElement": True,
        "NSHighResolutionCapable": True,
    },
)
