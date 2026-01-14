import os
import sys
import platform
from pathlib import Path
import re
import threading
import ctypes
import json


# --- Path Configuration ---
# This works for both MSYS2 dev and PyInstaller .exe
if os.name == 'nt':
    # Suppress D-Bus warning on Windows
    os.environ["DBUS_SESSION_BUS_ADDRESS"] = "null:"
    
if getattr(sys, 'frozen', False):
    base_path_app = sys._MEIPASS  # PyInstaller temporary extraction folder
else:
    base_path_app = os.path.dirname(os.path.abspath(__file__))

# --- GTK Imports ---
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import GLib, Gtk, Gdk, Pango, Adw

# --- 3. Project Modules ---
from UI.MainWindow import MainWindow
from Core.FFmpegParsers import (
    FFmpegFilterParser,
    FFmpegCodecParser,
    FFmpegFormatParser,
    FFmpegPixelFormatParser,
    FFmpegMediaInfoParser,
    FFmpegGlobalsParser
)

class FFGuiApp(Gtk.Application):
    def __init__(self, **kargs):
        super().__init__(application_id="com.kyo.ffgui", **kargs)
        GLib.set_application_name('ffGUI')

        self.wndMain = None
        self.ffmpeg_data = {}
        self.progress_win = None
        self.introspection_cancelled = False
    
        self.resolve_paths()
        self.setup_ffmpeg_execs()

        # Initialize Parsers
        self.parsers = {
            "globals": FFmpegGlobalsParser(self.ffmpeg_full_exec_path, self.cache_dir / "globals.json"),
            "codecs": FFmpegCodecParser(self.ffmpeg_full_exec_path, self.cache_dir / "codecs.json"),
            "pix_fmts": FFmpegPixelFormatParser(self.ffmpeg_full_exec_path, self.cache_dir / "pix_fmts.json"),
            "formats": FFmpegFormatParser(self.ffmpeg_full_exec_path, self.cache_dir / "formats.json"),
            "filters": FFmpegFilterParser(self.ffmpeg_full_exec_path, self.cache_dir / "filters.json"),
            "media": FFmpegMediaInfoParser(self.ffprobe_full_exec_path)
        }

    _ICONS_SETUP_DONE = False

    def _setup_windows_icons(self):
        if os.name != 'nt':
            return
            
        display = Gdk.Display.get_default()
        if display:
            theme = Gtk.IconTheme.get_for_display(display)
            
            # Point directly to the folder where the .svg files are located
            # Based on your structure, this is the 'actions' folder
            icon_dir = os.path.join(base_path_app, "gtk-icons", "hicolor", "scalable", "actions")
            
            if os.path.exists(icon_dir):
                # We add the direct folder to the search path
                theme.add_search_path(icon_dir)
                
                # Since there is no index.theme, GTK doesn't know 
                # to look for 'icon-name-symbolic.svg'. 
                # It only looks for 'icon-name.svg'.

            import winreg
            # Path to the Windows "Personalize" registry key
            try:
                # Access the Windows Registry key for 'Personalize'
                registry_path = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, registry_path) as key:
                    # AppsUseLightTheme: 0 = Dark Mode, 1 = Light Mode
                    value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
                    
                    style_manager = Adw.StyleManager.get_default()
                    if value == 0:
                        style_manager.set_color_scheme(Adw.ColorScheme.PREFER_DARK)
                    else:
                        style_manager.set_color_scheme(Adw.ColorScheme.PREFER_LIGHT)
            except Exception as e:
                print(f"Theme detection failed: {e}")
                # Default to system standard if registry check fails
                Adw.StyleManager.get_default().set_color_scheme(Adw.ColorScheme.PREFER_LIGHT)


    def _load_global_css(self):
        css_provider = Gtk.CssProvider()
        
        # Combine all your styles here
        global_css = """
            /* DispositionPickerWindow */
            .disposition-tag-pw {
                background-color: alpha(@theme_fg_color, 0.05);
                border: 1px solid mix(@theme_fg_color, @theme_bg_color, 0.8);
                border-radius: 6px;
                padding: 2px;
            }
            .disposition-tag-pw label {
                margin: 0 0 0 0;
                font-weight: bold;
                line-height: 100%;
            }
            .disposition-tag-pw:hover {
                background-color: alpha(@theme_selected_bg_color, 0.2);
                border-color: @theme_selected_bg_color;
            }

            /* JobSetupWindow */
            /* Target the rows inside the streams list specifically */
            #streams_list row:hover {
                background-color: transparent;
            }
            /* Optional: ensure they don't look 'selected' either since mode is NONE */
            #streams_list row:selected {
                background-color: transparent;
            }
                                    
            .container-tag {
                background-color: alpha(@theme_fg_color, 0.05);
                border: 1px solid mix(@theme_fg_color, @theme_bg_color, 0.8);
                border-radius: 6px;
                padding: 2px;
            }
            .container-tag label {
                margin: 0 6px 0 0;
                font-weight: bold;
                line-height: 100%;
            }
                                    
            .disposition-tag {
                background-color: alpha(@theme_fg_color, 0.05);
                border: 1px solid mix(@theme_fg_color, @theme_bg_color, 0.8);
                border-radius: 6px;
                padding: 6px 8px;
            }
            .disposition-tag label {
                margin: 0 0 0 0;
                font-weight: bold;
                line-height: 100%;
            }

            flowboxchild {
                padding: 0;
                margin: 0;
            }

            /* TemplateEditorWindow */
            .codec-tag { background-color: alpha(@theme_fg_color, 0.05); border: 1px solid mix(@theme_fg_color, @theme_bg_color, 0.8); border-radius: 6px; padding: 2px; }
            .codec-tag label { margin-left: 6px; margin-right: 6px; font-weight: bold; }
            dropdown > button > box > stack > row.activatable { background-color: transparent; }
            #template-editor-column popover box { min-width: 180px; }
            .warning-badge { 
                color: @warning_color; 
                border-radius: 4px; 
                padding: 2px 8px;
                font-size: 0.9em;
                font-weight: bold;
            }
        """
        
        css_provider.load_from_string(global_css)
        
        # Apply to the default display
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), 
            css_provider, 
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def resolve_paths(self):
        system = platform.system()
        app_name = "ffgui"

        if system == "Windows":
            self.base_dir = Path(os.environ.get("APPDATA", "~/AppData/Roaming")).expanduser() / app_name
            low_app_data = Path(os.environ.get("USERPROFILE", "~")).expanduser() / "AppData" / "LocalLow"
            self.cache_dir = low_app_data / app_name / "cache" / "ffmpeg"
        else:
            self.base_dir = Path("~/.config").expanduser() / app_name
            self.cache_dir = Path("~/.cache").expanduser() / app_name / "ffmpeg"

        # Portable Mode Check
        try:
            local_test = Path("./.write_test")
            local_test.touch()
            local_test.unlink()
            self.base_dir = Path("./")
            self.cache_dir = Path("./.cache/ffmpeg")
        except (OSError, PermissionError):
            pass

        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.settings_file = self.base_dir / "settings.yaml"
        self.templates_dir = self.base_dir / "templates"
        self.templates_dir.mkdir(exist_ok=True)
        self.codecs_dir = self.base_dir / "codecs"
        self.codecs_dir.mkdir(exist_ok=True)

    def setup_ffmpeg_execs(self):
        self.ffmpeg_path = ""
        self.ffmpeg_exec = "ffmpeg"
        self.ffprobe_exec = "ffprobe"

        if platform.system() == "Windows":
            if not self.ffmpeg_exec.endswith(".exe"): self.ffmpeg_exec += ".exe"
            if not self.ffprobe_exec.endswith(".exe"): self.ffprobe_exec += ".exe"

            if not self.ffmpeg_path:
                self.ffmpeg_full_exec_path = str(self.base_dir / Path("codecs") / Path("ffmpeg") / self.ffmpeg_exec)
                self.ffprobe_full_exec_path = str(self.base_dir / Path("codecs") / Path("ffmpeg") / self.ffprobe_exec)
            else:
                base = Path(self.ffmpeg_path)
                self.ffmpeg_full_exec_path = str(base / self.ffmpeg_exec)
                self.ffprobe_full_exec_path = str(base / self.ffprobe_exec)
        else:
            self.ffmpeg_full_exec_path = self.ffmpeg_exec
            self.ffprobe_full_exec_path = self.ffprobe_exec

    def do_startup(self):
        Gtk.Application.do_startup(self)
        self._setup_windows_icons()
        self._load_global_css()
        self.show_init_progress()

    def show_init_progress(self):
        self.progress_win = Gtk.Window(title="Initializing FFmpeg Data...", modal=True)
        self.progress_win.set_default_size(400, 120)
        self.progress_win.set_resizable(False)

        # Intercept the 'X' button
        self.progress_win.connect("close-request", self.on_window_close_request)

        header = Gtk.HeaderBar()
        header.set_show_title_buttons(True)
        self.progress_win.set_titlebar(header)

        vbox = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=10,
            margin_top=20, margin_bottom=20, margin_start=20, margin_end=20
        )

        self.prog_label = Gtk.Label(label="Starting introspection...", xalign=0)
        self.prog_bar = Gtk.ProgressBar(show_text=True)

        vbox.append(self.prog_label)
        vbox.append(self.prog_bar)

        btn_cancel = Gtk.Button(label="Cancel")
        btn_cancel.set_halign(Gtk.Align.END)
        btn_cancel.connect("clicked", lambda btn: self.on_cancel_request())
        vbox.append(btn_cancel)

        self.progress_win.set_child(vbox)
        GLib.idle_add(self._force_focus_progress)
        self.progress_win.present()

        thread = threading.Thread(target=self.run_introspection, daemon=True)
        thread.start()

    def _force_focus_progress(self):
        if self.progress_win:
            self.progress_win.present()
        return False # Only run once

    def on_window_close_request(self, window):
        self.on_cancel_request()
        return True # Prevent immediate destruction

    def on_cancel_request(self):
        dialog = Gtk.AlertDialog(
            message="Abort Initialization?",
            detail="The application cannot run without FFmpeg data. Do you want to quit?",
            buttons=["Continue", "Quit Application"]
        )
        dialog.choose(self.progress_win, None, self.on_cancel_confirmed)

    def on_cancel_confirmed(self, dialog, result):
        response = dialog.choose_finish(result)
        if response == 1:
            self.introspection_cancelled = True
            self.quit()

    def run_introspection(self):
        try:
            # Filter out the media parser for counting and processing
            cacheable_parsers = {k: v for k, v in self.parsers.items() if k != "media" and k != "dispositions"}
            total_parsers = len(cacheable_parsers)

            display_names = {
                "filters": "Filter", "codecs": "Codec",
                "formats": "Format", "pix_fmts": "Pixel Format"
            }

            for idx, (key, parser) in enumerate(cacheable_parsers.items()):
                if self.introspection_cancelled: return

                base_fraction = idx / total_parsers
                parser_weight = 1.0 / total_parsers
                prefix = display_names.get(key, "Processing")

                def granular_callback(msg):
                    if self.introspection_cancelled or not self.progress_win: return

                    clean_msg = re.sub(r'\x1b\[[0-9;]*[mK]', '', msg).replace('\r', '').strip()
                    item_match = re.search(r'\]\s+(.*)$', clean_msg)
                    display_text = f"{prefix}: {item_match.group(1)}" if item_match else clean_msg

                    progress_match = re.search(r"\[(\d+)/(\d+)\]", clean_msg)
                    if progress_match:
                        total_progress = base_fraction + (int(progress_match.group(1)) / int(progress_match.group(2)) * parser_weight)
                    else:
                        total_progress = base_fraction

                    GLib.idle_add(self.prog_label.set_text, display_text)
                    GLib.idle_add(self.prog_bar.set_fraction, total_progress)

                self.ffmpeg_data[key] = parser.get_all(progress_callback=granular_callback)

            # Add dispositions:
            disposition_json_path = self.base_dir / 'codecs' / 'ffmpeg_dispositions.json'
            dispositions = {}
            if os.path.exists(disposition_json_path):
                try:
                    with open(disposition_json_path, 'r', encoding='utf-8') as f:
                        dispositions = json.load(f)
                except Exception as e:
                    print("[WARNING] Could not load FFMPEG dispositions:\n" + e)
            self.ffmpeg_data["dispositions"] = dispositions

            GLib.idle_add(self.on_introspection_finished)
        except Exception as e:
            print(f"Introspection failed: {e}")
            GLib.idle_add(self.on_introspection_finished)

    def on_introspection_finished(self):
        if self.progress_win:
            self.progress_win.destroy()
            self.progress_win = None
        if not self.introspection_cancelled:
            if self.wndMain:
                self.wndMain.present()
            else:
                self.activate()

    def do_activate(self):
        if not self.wndMain:
            self.wndMain = MainWindow(application=self)
        self.wndMain.present()

if __name__ == "__main__":
    app = FFGuiApp()
    app.run()
