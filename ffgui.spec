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
    ('templates', 'templates'), # PyInstaller will put these in _internal initially
    ('codecs', 'codecs'),
    ('theme', 'theme'),
    ('LICENSE', '.'),
    (os.path.join(ucrt_lib, 'girepository-1.0'), 'lib/girepository-1.0'),
    (os.path.join(ucrt_lib, 'gdk-pixbuf-2.0'), 'lib/gdk-pixbuf-2.0'),
    (os.path.join(ucrt_share, 'glib-2.0/schemas'), 'share/glib-2.0/schemas'),
]

# optional_paths = [
#     (os.path.join(ucrt_share, 'icons/Adwaita'), 'share/icons/Adwaita'),
# ]
#
# for src, dst in optional_paths:
#     if os.path.exists(src):
#         all_datas.append((src, dst))

a = Analysis(
    ['ffgui.py'],
    pathex=[ucrt_bin],
    binaries=[],
    datas=all_datas,
    hiddenimports=['gi', 'gi.repository.Gtk', 'gi.repository.Adw', 'yaml', 'pycountry'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
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


DIST_PATH = os.path.abspath(os.path.join('dist', 'ffgui'))
INTERNAL_PATH = os.path.join(DIST_PATH, '_internal')

print("--- Step 2: Relocating assets and cleaning bloat ---")

# 1. Move folders that PyInstaller put in _internal to the root
to_move = ['templates', 'codecs', 'LICENSE']

for item in to_move:
    src = os.path.join(INTERNAL_PATH, item)
    dst = os.path.join(DIST_PATH, item)
    if os.path.exists(src):
        if os.path.exists(dst):
            shutil.rmtree(dst) if os.path.isdir(dst) else os.remove(dst)
        shutil.move(src, dst)
        print(f"Moved {item} to root.")

# 2. CLEAN UP THE DUPLICATE DLLS
# PyInstaller likely took your codecs and put them in _internal as loose files.
# We look for any 'av*.dll' in _internal and delete them because they are
# already safely inside ffgui/codecs/ffmpeg/ (thanks to 'all_datas')
print("--- Removing duplicate FFmpeg DLLs from _internal ---")
if os.path.exists(INTERNAL_PATH):
    for file in os.listdir(INTERNAL_PATH):
        # Only delete if it starts with 'av' and is a DLL
        # This targets ffmpeg specifically without touching GTK/System libs
        if file.startswith(('avfilter', 'avdevice', 'avcodec', 'avformat', 'avutil', 'swresample', 'swscale', 'postproc')) and file.endswith(".dll"):
            target = os.path.join(INTERNAL_PATH, file)
            os.remove(target)
            print(f"Deleted duplicate: {file}")

# 3. DELETE SOURCE CODE COPIES (Core and UI)
# If PyInstaller copied your source code folders into _internal, kill them.
for folder in ['Core', 'UI']:
    src_folder = os.path.join(INTERNAL_PATH, folder)
    if os.path.exists(src_folder):
        shutil.rmtree(src_folder)
        print(f"Removed source code duplicate: {folder}")
