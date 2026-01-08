import gi
import re
import os  # Added missing import
import threading
import platform
from pathlib import Path

gi.require_version("Gdk", "4.0")
gi.require_version("Gtk", "4.0")
from gi.repository import GLib, Gtk

# Assuming these exist in your project structure
from UI.MainWindow import MainWindow
from Core.FFmpegParsers import (
    FFmpegFilterParser,
    FFmpegCodecParser,
    FFmpegFormatParser,
    FFmpegPixelFormatParser
)

class FFGuiApp(Gtk.Application):
    def __init__(self, **kargs):
        super().__init__(application_id="com.kyo.ffgui", **kargs)
        GLib.set_application_name('ffGUI')

        self.wndMain = None
        self.ffmpeg_data = {}
        self.progress_win = None # Track window state

        self.resolve_paths()
        self.setup_ffmpeg_execs()

        # Debug prints for verification
        print(f"(i) Using Base Directory ... : {self.base_dir}")
        print(f"(i) Using Settings File .... : {self.settings_file}")
        print(f"(i) Using Templates Directory: {self.templates_dir}")
        print(f"(i) Using Codecs Directory . : {self.codecs_dir}")
        print(f"(i) Using Cache Directory .. : {self.cache_dir}")

        # Initialize Parsers using the resolved path
        self.parsers = {
            "filters": FFmpegFilterParser(self.ffmpeg_full_exec_path, self.cache_dir / "filters.json"),
            "codecs": FFmpegCodecParser(self.ffmpeg_full_exec_path, self.cache_dir / "codecs.json"),
            "formats": FFmpegFormatParser(self.ffmpeg_full_exec_path, self.cache_dir / "formats.json"),
            "pix_fmts": FFmpegPixelFormatParser(self.ffmpeg_full_exec_path, self.cache_dir / "pix_fmts.json")
        }

    def resolve_paths(self):
        """Determines where to store persistent settings vs transient cache."""
        system = platform.system()
        app_name = "ffgui"

        # Default System-specific paths
        if system == "Windows":
            self.base_dir = Path(os.environ.get("APPDATA", "~/AppData/Roaming")).expanduser() / app_name
            low_app_data = Path(os.environ.get("USERPROFILE", "~")).expanduser() / "AppData" / "LocalLow"
            self.cache_dir = low_app_data / app_name / "cache" / "ffmpeg"
        else:
            self.base_dir = Path("~/.config").expanduser() / app_name
            self.cache_dir = Path("~/.cache").expanduser() / app_name / "ffmpeg"

        # Portability Check: Try Local storage first
        try:
            # We check the current working directory
            local_test = Path("./.write_test")
            local_test.touch()
            local_test.unlink()

            self.base_dir = Path("./")
            self.cache_dir = Path("./.cache/ffmpeg")
        except (OSError, PermissionError):
            pass

        # Final Creation
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.settings_file = self.base_dir / "settings.json"
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
            self.ffmpeg_full_exec_path = self.ffmpeg_exec
            self.ffprobe_full_exec_path = self.ffprobe_exec
        else:
            base = Path(self.ffmpeg_path)
            self.ffmpeg_full_exec_path = str(base / self.ffmpeg_exec)
            self.ffprobe_full_exec_path = str(base / self.ffprobe_exec)

    def do_startup(self):
        Gtk.Application.do_startup(self)
        self.show_init_progress()

    def show_init_progress(self):
        """Creates a small window to show FFmpeg introspection progress."""
        self.progress_win = Gtk.Window(title="Initializing FFmpeg Data...", modal=True)
        self.progress_win.set_default_size(400, 120)
        self.progress_win.set_resizable(False)

        header = Gtk.HeaderBar()
        header.set_show_title_buttons(True)
        self.progress_win.set_titlebar(header)

        # Connect the window's close (X) button to our logic
        self.progress_win.connect("close-request", self.on_window_close_request)

        self.introspection_cancelled = False

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
        btn_cancel.connect("clicked", lambda btn: self.on_cancel_introspection())
        vbox.append(btn_cancel)

        self.progress_win.set_child(vbox)
        self.progress_win.present()

        thread = threading.Thread(target=self.run_introspection, daemon=True)
        thread.start()

    def on_window_close_request(self, window):
        """Triggered when the user clicks the 'X' button."""
        self.on_cancel_introspection()
        return True # Stop GTK from actually destroying the window immediately

    def on_cancel_introspection(self):
        """Shows a confirmation dialog before stopping and quitting."""
        # Create a simple confirmation dialog
        dialog = Gtk.AlertDialog(
            message="Abort Initialization?",
            detail="The application cannot run without FFmpeg data. Do you want to quit?",
            buttons=["Continue", "Quit Application"]
        )

        # Show the dialog and handle the response
        dialog.choose(self.progress_win, None, self.on_cancel_confirmed)

    def on_cancel_confirmed(self, dialog, result):
        response = dialog.choose_finish(result)
        if response == 1: # "Quit Application" index
            print("(i) Initialization aborted by user.")
            self.introspection_cancelled = True
            self.quit()

    def run_introspection(self):
        """Background thread worker with cancellation check."""
        try:
            total_parsers = len(self.parsers)
            display_names = {
                "filters": "Filter", "codecs": "Codec",
                "formats": "Format", "pix_fmts": "Pixel Format"
            }

            for idx, (key, parser) in enumerate(self.parsers.items()):
                # Check for cancellation at the start of every parser block
                if self.introspection_cancelled:
                    return

                base_fraction = idx / total_parsers
                parser_weight = 1.0 / total_parsers
                prefix = display_names.get(key, "Processing")

                def granular_callback(msg):
                    if self.introspection_cancelled or not self.progress_win:
                        return

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

            GLib.idle_add(self.on_introspection_finished)
        except Exception as e:
            print(f"Introspection failed: {e}")
            GLib.idle_add(self.on_introspection_finished)

    def on_introspection_finished(self):
        if self.progress_win:
            self.progress_win.destroy()
            self.progress_win = None
        self.activate()

    def do_activate(self):
        if not self.wndMain:
            self.wndMain = MainWindow(application=self)
        self.wndMain.present()

if __name__ == "__main__":
    app = FFGuiApp()
    app.run()
