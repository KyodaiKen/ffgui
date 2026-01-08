import gi
import yaml
import platform
from pathlib import Path

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio, GLib

class SettingsWindow(Gtk.Window):
    def __init__(self, parent, app_instance):
        super().__init__(title="Preferences", transient_for=parent, modal=True)
        self.set_default_size(500, -1)
        self.set_resizable(False)

        self.app = app_instance
        self.settings_file = self.app.settings_file

        vbox = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=12,
            margin_top=15, margin_bottom=15, margin_start=15, margin_end=15
        )
        self.set_child(vbox)

        # 1. Restart Hint
        self.restart_hint = Gtk.Frame()
        hint_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        hint_box.set_margin_start(10); hint_box.set_margin_end(10)
        hint_box.set_margin_top(8); hint_box.set_margin_bottom(8)

        hint_icon = Gtk.Image.new_from_icon_name("dialog-warning-symbolic")
        hint_label = Gtk.Label(label="Path changes require a restart to re-scan FFmpeg data.")
        hint_label.add_css_class("caption")

        hint_box.append(hint_icon)
        hint_box.append(hint_label)
        self.restart_hint.set_child(hint_box)
        self.restart_hint.set_visible(False)
        vbox.append(self.restart_hint)

        # 2. System Paths Section
        path_group = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        path_title = Gtk.Label(xalign=0)
        path_title.set_markup("<b>System Directories</b>")
        path_group.append(path_title)

        self.append_path_row(path_group, "Base Path:", str(self.app.base_dir))
        self.append_path_row(path_group, "Cache Path:", str(self.app.cache_dir))
        vbox.append(path_group)

        vbox.append(Gtk.Separator())

        # 3. FFmpeg Section (Calling the row builder here)
        ff_group = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        ff_title = Gtk.Label(xalign=0)
        ff_title.set_markup("<b>FFmpeg Executables Folder</b>")
        ff_group.append(ff_title)

        self.append_ffmpeg_row(ff_group)
        vbox.append(ff_group)

        # 4. Action Buttons
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        btn_box.set_halign(Gtk.Align.END)

        btn_cancel = Gtk.Button(label="Cancel")
        btn_cancel.connect("clicked", lambda x: self.close())

        btn_rescan = Gtk.Button(label="Save & Re-scan")
        btn_rescan.add_css_class("suggested-action") # Makes it stand out
        btn_rescan.connect("clicked", self.on_rescan_clicked)

        btn_save = Gtk.Button(label="Save & Close")
        btn_save.connect("clicked", self.on_save_clicked) # Calls validate_and_save then close

        btn_box.append(btn_cancel)
        btn_box.append(btn_rescan)
        btn_box.append(btn_save)
        vbox.append(btn_box)

        self.initial_path = ""
        self.load_settings()

    def append_path_row(self, container, label_text, path_text):
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        lbl = Gtk.Label(label=label_text, xalign=0)
        lbl.set_size_request(100, -1)
        entry = Gtk.Entry(text=path_text, editable=False, hexpand=True, can_focus=False)
        row.append(lbl)
        row.append(entry)
        container.append(row)

    def append_ffmpeg_row(self, container):
        """Creates the input row for the FFmpeg binary directory."""
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)

        self.entry_ff_path = Gtk.Entry(hexpand=True)
        self.entry_ff_path.set_placeholder_text("Default (System PATH)")
        self.entry_ff_path.connect("changed", self.on_path_changed)

        btn_browse = Gtk.Button(icon_name="folder-open-symbolic")
        btn_browse.set_tooltip_text("Select folder containing ffmpeg and ffprobe")
        btn_browse.connect("clicked", self.on_browse_clicked)

        row.append(self.entry_ff_path)
        row.append(btn_browse)
        container.append(row)

    def on_browse_clicked(self, button):
        """Native folder picker."""
        native = Gtk.FileChooserNative.new(
            title="Select Folder containing FFmpeg Executables",
            parent=self,
            action=Gtk.FileChooserAction.SELECT_FOLDER, # Changed to folder selection
            accept_label="_Select Folder",
            cancel_label="_Cancel",
        )
        native.connect("response", self.on_file_chooser_response)
        native.show()

    def on_file_chooser_response(self, native, response):
        if response == Gtk.ResponseType.ACCEPT:
            folder = native.get_file()
            self.entry_ff_path.set_text(folder.get_path())
        native.destroy()

    def on_path_changed(self, entry):
        is_changed = entry.get_text().strip() != self.initial_path
        self.restart_hint.set_visible(is_changed)

    def load_settings(self):
        if self.settings_file.exists():
            try:
                with open(self.settings_file, 'r') as f:
                    data = yaml.safe_load(f) or {}
                    self.initial_path = data.get("ffmpeg_path", "")
                    self.entry_ff_path.set_text(self.initial_path)
            except Exception as e:
                print(f"Load error: {e}")

    def on_rescan_clicked(self, button):
        """Saves settings and triggers a fresh introspection immediately."""
        # 1. Reuse the validation logic
        if not self.validate_and_save():
            return # Stop if validation failed

        # 2. Hide the main window and settings window
        if self.app.wndMain:
            self.app.wndMain.hide()
        self.close()

        # 3. Clear old data and restart the progress flow
        self.app.ffmpeg_data = {}
        self.app.show_init_progress()

    def validate_and_save(self):
        """Extracted validation logic to return True/False."""
        new_path_str = self.entry_ff_path.get_text().strip()

        if new_path_str:
            path_obj = Path(new_path_str)
            ext = ".exe" if platform.system() == "Windows" else ""

            if not path_obj.is_dir():
                self.show_error("Invalid Path", "The selected path is not a directory.")
                return False

            for binary in [f"ffmpeg{ext}", f"ffprobe{ext}"]:
                if not (path_obj / binary).exists():
                    self.show_error("Missing Executable", f"Could not find {binary} in folder.")
                    return False

        # Save to YAML
        try:
            with open(self.settings_file, 'w') as f:
                yaml.dump({"ffmpeg_path": new_path_str}, f)
            self.app.ffmpeg_path = new_path_str
            self.app.setup_ffmpeg_execs()
            return True
        except Exception as e:
            self.show_error("Save Error", str(e))
            return False

    def on_save_clicked(self, button):
        """Validates the path and saves settings."""
        new_path_str = self.entry_ff_path.get_text().strip()

        # 1. Validation Logic
        if new_path_str: # Only validate if a custom path is provided
            path_obj = Path(new_path_str)

            # Define filenames based on OS
            ext = ".exe" if platform.system() == "Windows" else ""
            ffmpeg_name = f"ffmpeg{ext}"
            ffprobe_name = f"ffprobe{ext}"

            # Check if directory exists and contains binaries
            missing = []
            if not path_obj.is_dir():
                self.show_error("Invalid Path", f"The path '{new_path_str}' is not a valid directory.")
                return

            if not (path_obj / ffmpeg_name).exists():
                missing.append(ffmpeg_name)
            if not (path_obj / ffprobe_name).exists():
                missing.append(ffprobe_name)

            if missing:
                self.show_error(
                    "Missing Executables",
                    f"Could not find {', '.join(missing)} in the selected folder."
                )
                return

        # 2. Save Logic (if validation passes or path is empty)
        settings_data = {"ffmpeg_path": new_path_str}
        try:
            with open(self.settings_file, 'w') as f:
                yaml.dump(settings_data, f)

            self.app.ffmpeg_path = new_path_str
            self.app.setup_ffmpeg_execs()
            self.close()
        except Exception as e:
            self.show_error("Save Error", f"Failed to write settings file: {e}")

    def show_error(self, title, message):
        """Helper to show a simple error alert."""
        alert = Gtk.AlertDialog(
            message=title,
            detail=message,
            buttons=["OK"]
        )
        alert.show(self)
