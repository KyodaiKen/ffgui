import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gdk, Pango

class ContainerPickerWindow(Gtk.ApplicationWindow):
    def __init__(self, parent_window, current_val, on_select, **kwargs):
        super().__init__(**kwargs, title="Select Output Container")

        # Safely get the application instance
        self.app = parent_window.get_application()
        if not self.app:
            # Fallback if the window isn't fully realized yet
            self.app = Gtk.Application.get_default()

        self.on_select = on_select
        self.set_default_size(450, 500)
        self.set_transient_for(parent_window)
        self.set_modal(True)

        self.active_types = self.get_active_stream_types()
        
        # 1. Search Header
        hb = Gtk.HeaderBar()
        self.set_titlebar(hb)
        self.search_entry = Gtk.SearchEntry(placeholder_text="Search container (e.g. mp4, mkv)...")
        self.search_entry.connect("search-changed", self.on_search_changed)
        self.search_entry.connect("activate", lambda _: self.on_ok_clicked())
        hb.set_title_widget(self.search_entry)

        # 2. Layout
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        main_box.props.margin_start = 6
        main_box.props.margin_end = 6
        main_box.props.margin_top = 6
        main_box.props.margin_bottom = 6
        self.set_child(main_box)

        self.lst_formats = Gtk.ListBox()
        self.lst_formats.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.lst_formats.set_activate_on_single_click(False)
        self.lst_formats.connect("row-activated", lambda *_: self.on_ok_clicked())
        
        scroll = Gtk.ScrolledWindow(vexpand=True)
        scroll.set_child(self.lst_formats)
        main_box.append(scroll)

        self.btn_select = Gtk.Button(label="Select Container", cursor=Gdk.Cursor.new_from_name("pointer", None))
        self.btn_select.add_css_class("suggested-action")
        self.btn_select.connect("clicked", lambda _: self.on_ok_clicked())
        main_box.append(self.btn_select)

        # 3. Data Population
        self.populate_list()
        self.search_entry.grab_focus()

    def get_active_stream_types(self):
        """Finds what types of streams (video, audio, subtitle) are checked 'active'."""
        types = set()
        parent = self.get_transient_for()
        # Access the stream selection dictionary from JobSetupWindow
        if hasattr(parent, 'selected_streams'):
            for stream_key, settings in parent.selected_streams.items():
                if settings.get("active"):
                    # We need the type. SourceStreamRow usually stores this.
                    # If not available directly in settings, we infer from parent rows.
                    row = self._find_row_by_key(parent, stream_key)
                    if row and hasattr(row, 'stream_type'):
                        types.add(row.stream_type.lower())
        return types

    def _find_row_by_key(self, parent, key):
        """Helper to find the specific SourceStreamRow in the parent's list."""
        child = parent.lst_source_streams.get_first_child()
        while child:
            if hasattr(child, 'source_path') and (child.source_path, child.stream_index) == key:
                return child
            child = child.get_next_sibling()
        return None

    def populate_list(self, filter_text=""):
        while child := self.lst_formats.get_first_child():
            self.lst_formats.remove(child)

        search = filter_text.lower()

        # Add "auto" option
        if not search or "auto" in search:
            self.add_format_row("auto", "Automatic (Inferred from extension)")

        # Access cached ffmpeg data
        formats_list = getattr(self.app, 'ffmpeg_data', {}).get('formats', [])

        for fmt in formats_list:
            # 1. Filter: Must be a muxer (output)
            if not fmt.get('is_muxer'):
                continue

            # 2. Filter: Search string
            name = fmt.get('name', '')
            descr = fmt.get('descr', '')
            if search and (search not in name.lower() and search not in descr.lower()):
                continue

            # 3. Filter: Capability check
            # Only show formats that support the streams we have active.
            # (e.g., if we have Audio, don't show 'image2' muxer)
            if not self._format_supports_active_types(fmt):
                continue

            if name.lower() != "auto":
                self.add_format_row(name, descr)

    def _format_supports_active_types(self, fmt):
        """
        Logic to determine if the container can handle the selected streams.
        FFmpeg formats often have flags: 'V' (Video), 'A' (Audio), 'S' (Sub).
        """
        # If no streams are active yet, show everything
        if not self.active_types:
            return True

        # Mapping our internal types to FFmpeg capability flags
        # These flags are usually found in the 'capabilities' or 'descr' 
        # depending on how you parsed your JSON.
        # Assuming fmt['capabilities'] contains ['video', 'audio', etc]
        caps = fmt.get('capabilities', [])
        
        # Basic logical check: If the format is strictly video-only (like many image muxers)
        # but we have audio active, we should skip it.
        if 'audio' in self.active_types and 'audio' not in caps and len(caps) > 0:
            return False
            
        return True

    def add_format_row(self, fmt_id, long_name):
        row_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12, margin_top=6, margin_bottom=6)

        lbl_id = Gtk.Label(xalign=0, width_chars=12)
        lbl_id.set_markup(f"<b>{fmt_id}</b>")

        lbl_name = Gtk.Label(label=long_name, xalign=0, ellipsize=Pango.EllipsizeMode.END)

        row_box.append(lbl_id)
        row_box.append(lbl_name)

        list_row = Gtk.ListBoxRow()
        list_row.set_child(row_box)
        list_row._data = fmt_id
        self.lst_formats.append(list_row)

    def on_search_changed(self, entry):
        self.populate_list(entry.get_text())

    def on_ok_clicked(self):
        row = self.lst_formats.get_selected_row()
        if row:
            self.on_select(row._data)
            self.destroy()