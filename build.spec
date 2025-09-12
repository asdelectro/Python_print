# -*- mode: python ; coding: utf-8 -*-
# Updated Spec file for Data Matrix label printer

import os
from PyInstaller.utils.hooks import collect_submodules, collect_data_files
reportlab_hiddenimports = collect_submodules('reportlab')

critical_reportlab_modules = [
    'reportlab.pdfgen.canvas',
    'reportlab.lib.units',
    'reportlab.graphics.renderPDF',
    'reportlab.graphics.shapes',
    'reportlab.graphics.barcode.common',
    'reportlab.graphics.barcode',
    'reportlab.graphics',
]

datamatrix_modules = [
    'pylibdmtx.pylibdmtx',
    'pylibdmtx',
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[
        ('RCDevices.dll', '.'),  
    ],
    datas=[
        ('templates', 'templates'), 
        ('static', 'static'),      
        ('print_labels.py', '.'),  
        ('hardware.py', '.'),       
        ('conf.toml', '.'),         
        ('template51x25.pdf', '.'), 
    ] + collect_data_files('reportlab'), 
    hiddenimports=[
        'flask',
        'flask.templating',
        'jinja2',
        'werkzeug',
        'requests',     
        'hardware',
        'print_labels',
        'PyPDF2',
        'PIL.Image',
        'PIL.ImageWin',  
        'psycopg2',
        'psycopg2._psycopg',
        'psycopg2.extensions',
        'win32print',
        'win32ui',
        'pythoncom',
        'pywintypes',
        'toml',
        'pylibdmtx',
        'pylibdmtx.pylibdmtx',
        'socket',
        'datetime',
        'logging',
        'subprocess',
        'ctypes',
        'platform',
        
    ] + reportlab_hiddenimports + critical_reportlab_modules,
    hookspath=['.'],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

reportlab_found = any('reportlab' in str(imp) for imp in a.pure)
flask_found = any('flask' in str(imp) for imp in a.pure)
print(f"ReportLab moduke found: {reportlab_found}")
print(f"Flask Module found: {flask_found}")

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