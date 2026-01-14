# -*- mode: python ; coding: utf-8 -*-
import os
import shutil
import subprocess
from PyInstaller.building.api import EXE, PYZ, COLLECT
from PyInstaller.building.build_main import Analysis

def to_win(path):
    return subprocess.check_output(['cygpath', '-w', path]).decode().strip()

ucrt_bin = to_win('/ucrt64/bin')
ucrt_lib = to_win('/ucrt64/lib')
ucrt_share = to_win('/ucrt64/share')

all_datas = [
    ('gtk-icons', 'gtk-icons'),
    ('UI', 'UI'),
    ('Core', 'Core'),
    ('templates', 'templates'), # PyInstaller will put these in _internal initially
    ('codecs', 'codecs'),
    ('LICENSE', '.'),
    (os.path.join(ucrt_lib, 'girepository-1.0'), 'lib/girepository-1.0'),
    (os.path.join(ucrt_lib, 'gdk-pixbuf-2.0'), 'lib/gdk-pixbuf-2.0'),
    (os.path.join(ucrt_share, 'glib-2.0/schemas'), 'share/glib-2.0/schemas'),
]

optional_paths = [
    (os.path.join(ucrt_share, 'icons/Adwaita'), 'share/icons/Adwaita'),
]

for src, dst in optional_paths:
    if os.path.exists(src):
        all_datas.append((src, dst))

a = Analysis(
    ['ffgui.py'],
    pathex=[ucrt_bin],
    binaries=[],
    datas=all_datas,
    hiddenimports=['gi', 'gi.repository.Gtk', 'gi.repository.Adw', 'yaml', 'pycountry'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

essential_dlls = [
    'libpython3.13.dll', 'libgtk-4-1.dll', 'libadwaita-1-0.dll',
    'libglib-2.0-0.dll', 'libgobject-2.0-0.dll', 'libgio-2.0-0.dll',
    'libwinpthread-1.dll', 'libgcc_s_seh-1.dll', 'libstdc++-6.dll',
    'libintl-8.dll', 'libiconv-2.dll', 'libpango-1.0-0.dll',
    'libcairo-2.dll', 'libharfbuzz-0.dll', 'libgdk_pixbuf-2.0-0.dll',
    'libepoxy-0.dll', 'libfribidi-0.dll'
]

for dll in essential_dlls:
    dll_path = os.path.join(ucrt_bin, dll)
    if os.path.exists(dll_path):
        a.binaries.append((dll, dll_path, 'BINARY'))

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ffgui',
    debug=False,
    console=True,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name='ffgui',
)

# --- THE FIX: POST-BUILD MANIPULATION ---
DIST_PATH = os.path.join('dist', 'ffgui')
INTERNAL_PATH = os.path.join(DIST_PATH, '_internal')

to_move = ['templates', 'codecs', 'LICENSE']

print("--- Moving files to root directory ---")
for item in to_move:
    src = os.path.join(INTERNAL_PATH, item)
    dst = os.path.join(DIST_PATH, item)
    if os.path.exists(src):
        # If it's a folder, remove destination if it exists and move
        if os.path.isdir(src):
            if os.path.exists(dst):
                shutil.rmtree(dst)
            shutil.move(src, dst)
            print(f"Moved directory: {item}")
        else:
            # If it's a file
            shutil.move(src, dst)
            print(f"Moved file: {item}")
