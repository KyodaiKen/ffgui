import gi

from UI.Builder import Builder
gi.require_version("Gdk", "4.0")
from gi.repository import Gtk, Pango
from UI.MetadataManagerWindow import MetadataManagerWindow
from UI.FlagsPickerWindow import FlagsPickerWindow
from UI.LanguagePickerWindow import LanguagePickerWindow
from Core.Utils import seconds_to_time, time_to_seconds

class SourceStreamRow(Gtk.ListBoxRow):
    def __init__(self, stream_descr, stream_type, source_path, stream_index, parent_window, initial_metadata, initial_disposition, raw_duration):
        super().__init__()

        # Convert the high-precision string tag or float to seconds
        if isinstance(raw_duration, str) and ":" in raw_duration:
            self.total_duration = time_to_seconds(raw_duration)
        else:
            try:
                self.total_duration = float(raw_duration or 0)
            except ValueError:
                self.total_duration = 0.0

        self.source_path = source_path
        self.stream_type = stream_type
        self.stream_index = stream_index
        self.parent_window = parent_window
        self.stream_metadata = initial_metadata if initial_metadata is not None else {}
        self.stream_disposition = initial_disposition if initial_disposition is not None else {}
        self.trim_start = ""
        self.trim_length = ""
        self.trim_end = ""
        self.stream_delay = 0.0

        # Flag to track if the user has modified start yet
        self._start_modified_once = False

        # Layout
        grid = Gtk.Grid(orientation=Gtk.Orientation.VERTICAL, row_spacing=6, column_spacing=6)
        grid.set_hexpand(True)
        self.set_child(grid)

        # Left checkbox
        self.chk = Gtk.CheckButton()
        grid.attach(self.chk, 0, 0, 1, 1)

        # Label for stream
        self.lbl_strm = Gtk.Label(xalign=0, label=f"<b>{stream_descr}</b>", use_markup=True,)
        self.lbl_strm.set_ellipsize(Pango.EllipsizeMode.END)
        grid.attach(self.lbl_strm, 1, 0, 2, 1)

        # Tag button for stream meta data
        self.btn_meta = Gtk.Button(icon_name="tag-symbolic", halign=Gtk.Align.END, tooltip_text="Setup Stream Metadata")
        self.btn_meta.set_margin_end(24)
        grid.attach(self.btn_meta, 3, 0, 1, 1) 
        self.btn_meta.connect("clicked", self.on_manage_meta)
        # Highlight button if metadata exists initially
        self.update_meta_button_style()


        # Create a Sub-Grid for grouped output elements
        self.tpl_lng_subgrid = Gtk.Grid(column_spacing=4, row_spacing=4, hexpand=True)
        grid.attach(self.tpl_lng_subgrid, 1, 1, 3, 1)

        # ------ ROW1 ------
        # --- Headers ---
        self.lbl_tpl = Gtk.Label(xalign=0, label="Transcoding Template")
        self.lbl_lng = Gtk.Label(xalign=0, label="Language")
        self.tpl_lng_subgrid.attach(self.lbl_tpl, 0, 0, 2, 1)
        self.tpl_lng_subgrid.attach(self.lbl_lng, 2, 0, 2, 1)

        # Entry for template
        self.ent_tpl = Gtk.Entry(hexpand=True, halign=Gtk.Align.FILL)
        self.ent_tpl.set_editable(False)
        self.ent_tpl.set_can_focus(False)
        self.tpl_lng_subgrid.attach(self.ent_tpl, 0, 1, 1, 1)

        # Button for search
        self.btn_srch = Gtk.Button(icon_name="search-symbolic", halign=Gtk.Align.END)
        self.btn_srch.set_margin_end(12)
        self.btn_srch.connect("clicked", self.on_search_tpl_click)
        self.tpl_lng_subgrid.attach(self.btn_srch, 1, 1, 1, 1)

        # Entry for language
        self.ent_lng = Gtk.Entry(hexpand=False, halign=Gtk.Align.START)
        self.ent_lng.props.max_length=3
        self.ent_lng.props.width_chars = 3
        self.ent_lng.props.max_width_chars=3
        self.tpl_lng_subgrid.attach(self.ent_lng, 2, 1, 1, 1)

        # Button for search
        self.btn_srch_lng = Gtk.Button(icon_name="search-symbolic", halign=Gtk.Align.END)
        self.btn_srch_lng.set_margin_end(24)
        self.btn_srch_lng.connect("clicked", self.on_search_lng_click)
        self.tpl_lng_subgrid.attach(self.btn_srch_lng, 3, 1, 1, 1)

        # Back to the main grid
        # Label "Disposition"
        self.lbl_dsp = Gtk.Label(halign=Gtk.Align.END, label="Disposition:")
        grid.attach(self.lbl_dsp, 1, 2, 1, 1)

        # disposition
        self.dispositions = self.create_disposition_pills(self.stream_disposition)
        grid.attach(self.dispositions, 2, 2, 1, 1)

        # Button for adding
        self.btn_add_dsp = Gtk.Button(icon_name="search-symbolic", halign=Gtk.Align.END)
        self.btn_add_dsp.set_margin_end(24)
        grid.attach(self.btn_add_dsp, 3, 2, 1, 1)
        self.btn_add_dsp.connect("clicked", self.on_add_dsp_click)

        # ------ ROW2 ------
        # Create a Sub-Grid for grouped output elements
        self.tpl_trim = Gtk.Grid(column_spacing=12, row_spacing=4, hexpand=True)
        grid.attach(self.tpl_trim, 1, 3, 3, 1)

        # --- Headers ---
        self.lbl_tstart = Gtk.Label(xalign=0, label="Trim Start (HH:MM:SS.FFF)")
        self.lbl_tlen = Gtk.Label(xalign=0, label="Trim Length (HH:MM:SS.FFF)")
        self.lbl_tend = Gtk.Label(xalign=0, label="Trim End (HH:MM:SS.FFF)")
        self.lbl_sdly = Gtk.Label(xalign=0, label="Stream Delay (ms)")
        self.tpl_trim.attach(self.lbl_tstart, 0, 2, 1, 1)
        self.tpl_trim.attach(self.lbl_tlen, 1, 2, 1, 1)
        self.tpl_trim.attach(self.lbl_tend, 2, 2, 1, 1)
        self.tpl_trim.attach(self.lbl_sdly, 3, 2, 1, 1)

        # --- Entries ---
        self.ent_tstart = Gtk.Entry(hexpand=True, halign=Gtk.Align.FILL, placeholder_text="00:00:00.000")
        self.tpl_trim.attach(self.ent_tstart, 0, 3, 1, 1)

        self.ent_tlen = Gtk.Entry(hexpand=True, halign=Gtk.Align.FILL, placeholder_text="00:00:00.000")
        self.tpl_trim.attach(self.ent_tlen, 1, 3, 1, 1)

        self.ent_tend = Gtk.Entry(hexpand=True, halign=Gtk.Align.FILL, placeholder_text="00:00:00.000")
        self.tpl_trim.attach(self.ent_tend, 2, 3, 1, 1)

        self.ent_sdly = Gtk.Entry(hexpand=True, halign=Gtk.Align.FILL, placeholder_text="0")
        self.ent_sdly.set_margin_end(24)
        self.tpl_trim.attach(self.ent_sdly, 3, 3, 1, 1)

        # Flag to prevent infinite loops during cross-calculation
        self._is_calculating = False

        # Connect signals
        self.ent_tstart.connect("changed", self.on_trim_time_changed)
        self.ent_tlen.connect("changed", self.on_trim_len_changed)
        self.ent_tend.connect("changed", self.on_trim_end_changed)


    def on_add_dsp_click(self, button):
        # 1. Get the list of all possible FFmpeg disposition flags from app data
        # Assuming your app instance has the ffmpeg_data dict populated
        options = getattr(self.parent_window.app, 'ffmpeg_data', {}).get('dispositions', {}).get('options', [])
        
        # 2. Open the FlagsPickerWindow
        self.pw = FlagsPickerWindow(
            parent=self.parent_window,
            options=options,
            current_values=self.stream_disposition, # Pass existing flags
            strings={
                "title": "Select Stream Dispositions",
                "placeholder_text": "Search dispositions (e.g. default, forced)..."
            },
            on_apply=self.apply_disposition
        )
        self.pw.present()

    def apply_disposition(self, selected_flags):
        # Store the list of selected flags
        self.stream_disposition = selected_flags
        
        # Clear the FlowBox UI
        while child := self.dispositions.get_first_child():
            self.dispositions.remove(child)
            
        # Rebuild with the fresh list using the Builder
        # The Builder.build_pill method handles the list -> UI conversion
        Builder.build_pill(self.dispositions, self.stream_disposition)

    def on_search_lng_click(self, button):
        # We pass the callback exactly like we did for the Disposition picker
        self.pw = LanguagePickerWindow(
            parent_window = self.parent_window,
            current_val=self.ent_lng.get_text(),
            on_select=self.apply_language
        )
        self.pw.present()

    def apply_language(self, selected_code):
        self.ent_lng.set_text(selected_code)

    def update_meta_button_style(self):
        if self.stream_metadata:
            self.btn_meta.add_css_class("suggested-action")
        else:
            self.btn_meta.remove_css_class("suggested-action")

    def on_manage_meta(self, _):
        win = MetadataManagerWindow(self.parent_window, self.stream_metadata, self.save_meta)
        win.present()

    def save_meta(self, meta):
        self.stream_metadata = meta
        self.update_meta_button_style()

    def on_search_tpl_click(self, button):
        from UI.TemplatePickerWindow import TemplatePickerWindow
        self.pw = TemplatePickerWindow(
            parent_window=self.parent_window,
            current_val=self.ent_tpl.get_text(),
            stream_type=self.stream_type,
            on_select=self.apply_template
        )
        self.pw.present()

    def apply_template(self, template_name):
        self.ent_tpl.set_text(template_name)

    def create_disposition_pills(self, disposition_str):
        """Initial creation of the container during row setup."""
        self.dispositions = Gtk.FlowBox(
            orientation=Gtk.Orientation.HORIZONTAL,
            selection_mode=Gtk.SelectionMode.NONE,
            column_spacing=6,   # This sets your 6px horizontal gap
            row_spacing=6,      # This sets your 6px vertical gap
            homogeneous=False,  # Allow tags to have different widths
            halign=Gtk.Align.START,
            hexpand = True
        )
        self.dispositions.set_margin_start(0)
        self.dispositions.set_margin_end(0)
        self.dispositions.set_margin_top(0)
        self.dispositions.set_margin_bottom(0)
        Builder.build_pill(self.dispositions, disposition_str)
        return self.dispositions

    def on_trim_time_changed(self, _):
        if self._is_calculating: return

        # Initial Auto-fill Logic (Keep this as is, it's working well)
        if not self._start_modified_once:
            current_end_val = time_to_seconds(self.ent_tend.get_text())
            if current_end_val == 0:
                self._is_calculating = True
                start_sec = time_to_seconds(self.ent_tstart.get_text())
                precise_end_str = seconds_to_time(self.total_duration)
                precise_len_str = seconds_to_time(max(0, self.total_duration - start_sec))
                
                self.ent_tend.set_text(precise_end_str)
                self.ent_tlen.set_text(precise_len_str)
                
                self._is_calculating = False
                self._start_modified_once = True
                return 

        # NEW LOGIC: When Start changes LATER, update the Length, keep the End fixed
        self._sync_len_from_start_and_end()

    def on_trim_len_changed(self, _):
        """When Length changes, update End."""
        if self._is_calculating: return
        self._sync_end_from_start_and_len()

    def on_trim_end_changed(self, _):
        """When End changes, update Length."""
        if self._is_calculating: return
        self._is_calculating = True
        
        start_sec = time_to_seconds(self.ent_tstart.get_text())
        end_sec = time_to_seconds(self.ent_tend.get_text())
        
        new_len = max(0, end_sec - start_sec)
        self.ent_tlen.set_text(seconds_to_time(new_len))
        
        self._is_calculating = False

    def _sync_len_from_start_and_end(self):
        """Calculates Length = End - Start (Keeps End fixed)"""
        if self._is_calculating: return
        
        self._is_calculating = True
        start_sec = time_to_seconds(self.ent_tstart.get_text())
        end_sec = time_to_seconds(self.ent_tend.get_text())
        
        # Calculate the new length
        new_len = max(0, end_sec - start_sec)
        self.ent_tlen.set_text(seconds_to_time(new_len))
        self._is_calculating = False

    def get_stream_config(self):
        """Returns the configuration for this stream to be stored in the Job."""
        return {
            "active": self.chk.get_active(),
            "index": self.stream_index,
            "type": self.stream_type,
            "template": self.ent_tpl.get_text(),
            "language": self.ent_lng.get_text(),
            "disposition": self.stream_disposition,
            "metadata": self.stream_metadata,
            "trim_start": self.ent_tstart.get_text().strip(),
            "trim_length": self.ent_tlen.get_text().strip(),
            "trim_end": self.ent_tend.get_text().strip(),
            "stream_delay": self.ent_sdly.get_text().strip() or "0"
        }