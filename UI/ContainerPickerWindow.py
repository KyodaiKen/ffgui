import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gdk, Pango
import av.format

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

        self.required_codecs = self.get_active_codecs(parent_window)
        
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
        self.formats = []
        for name in sorted(av.format.formats_available):
            fmt = av.format.ContainerFormat(name)
            if fmt.is_output:
                self.formats.append({"id": name, "long": fmt.long_name})

        self.populate_list()
        self.search_entry.grab_focus()

    def get_active_codecs(self, parent):
        """Identifies which codecs are currently selected for output."""
        active_codecs = set()
        row = parent.lst_source_streams.get_first_child()
        while row:
            if hasattr(row, 'chk') and row.chk.get_active():
                # We need the codec name from the stream data
                key = (row.source_path, row.stream_index)
                stream_data = parent.selected_streams.get(key)
                if stream_data:
                    # Logic here depends on if user is 'copying' or 'encoding'
                    # For now, we'll assume we check against the source codec
                    pass
            row = row.get_next_sibling()
        return active_codecs

    def get_active_stream_types(self):
        """Helper to find what types of streams are checked in the parent UI."""
        types = set()
        parent = self.get_transient_for()
        if hasattr(parent, 'lst_source_streams'):
            row = parent.lst_source_streams.get_first_child()
            while row:
                if hasattr(row, 'chk') and row.chk.get_active():
                    # Get type from the SourceStreamRow attribute
                    types.add(row.stream_type)
                row = row.get_next_sibling()
        return types

    def populate_list(self, filter_text=""):
        while child := self.lst_formats.get_first_child():
            self.lst_formats.remove(child)

        search = filter_text.lower()

        # --- ALWAYS add "auto" first ---
        if not search or "auto" in search:
            self.add_format_row("auto", "Automatic (Inferred from extension)")

        # Access the raw list from the formats.json cache
        formats_list = self.app.ffmpeg_data.get('formats', [])

        for fmt in formats_list:
            if not fmt.get('is_muxer'): continue

            name = fmt.get('name', '')
            descr = fmt.get('descr', '')

            if search in name.lower() or search in descr.lower():
                # Avoid duplicates if a real format is named 'auto'
                if name.lower() != "auto":
                    self.add_format_row(name, descr)

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
