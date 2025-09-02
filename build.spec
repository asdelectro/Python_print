# -*- mode: python ; coding: utf-8 -*-
# ПРИНУДИТЕЛЬНЫЙ Spec-файл для QR модуля

import os
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

# Собираем ВСЕ модули ReportLab принудительно
reportlab_hiddenimports = collect_submodules('reportlab')

# Принудительно добавляем критически важные модули
critical_modules = [
    'reportlab.graphics.barcode.qr',
    'reportlab.graphics.barcode.common', 
    'reportlab.graphics.barcode',
    'reportlab.graphics',
    'reportlab.pdfgen.canvas',
    'reportlab.lib.units',
    'reportlab.graphics.renderPDF',
    'reportlab.graphics.shapes',
]

a = Analysis(
    ['desk_main.py'],
    pathex=[],
    binaries=[
        ('libmysql64.dll', '.'),
        ('RCDevices.dll', '.'),
        ('RCDevices.lib', '.'),
    ],
    datas=[
        ('templates', 'templates'),
        ('hardware.py', '.'),
        ('print_labels.py', '.'),
        ('templ_103.pdf', '.'),
    ] + collect_data_files('reportlab'),  # Добавляем все файлы данных ReportLab
    hiddenimports=[
        # Базовые модули
        'hardware',
        'print_labels',
        'flask',
        'requests', 
        'PyPDF2',
        'fitz',
        'PIL.Image',
        'PIL.ImageWin',
        'psycopg2',
        'win32print',
        'win32ui',
        'webview',
        'webview.platforms.cef',
        'webview.platforms.winforms',
        'pythoncom',
        'pywintypes',
    ] + reportlab_hiddenimports + critical_modules,  # Объединяем все списки
    hookspath=['.'],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['pylibdmtx'],
    noarchive=False,
)

# Проверяем, что QR модуль точно включен
qr_found = any('reportlab.graphics.barcode.qr' in str(imp) for imp in a.pure)
print(f"QR модуль найден в сборке: {qr_found}")

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='LabelPrinter',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)