import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gio

class FilterPickerWindow(Gtk.ApplicationWindow):
    def __init__(self, parent_window, stream_type, on_select):
        super().__init__(title="Select Filter", transient_for=parent_window, modal=True)
        self.set_default_size(450, 600)
        self.on_select = on_select
        
        # 1. Setup Header Bar with Search
        header = Gtk.HeaderBar()
        self.set_titlebar(header)
        
        self.search_entry = Gtk.SearchEntry(placeholder_text="Search name or description...")
        self.search_entry.set_size_request(250, -1)
        header.set_title_widget(self.search_entry)

        # 2. Get data from app
        app = Gtk.Application.get_default()
        all_filters = getattr(app, 'ffmpeg_data', {}).get('filters', [])
        
        # Initial filter by stream type
        self.available_filters = [
            f for f in all_filters 
            if stream_type in f.get('inputs', []) or not f.get('inputs')
        ]

        # 3. Build UI
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_child(main_box)

        scroll = Gtk.ScrolledWindow(vexpand=True)
        self.listbox = Gtk.ListBox()
        self.listbox.add_css_class("boxed-list")
        scroll.set_child(self.listbox)
        main_box.append(scroll)

        # 4. Populate List
        for f in self.available_filters:
            row = Gtk.ListBoxRow()
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, margin_start=10, margin_end=10, margin_top=8, margin_bottom=8)
            
            # Use lowercase storage for faster searching
            row._search_key = f"{f['name']} {f['descr']}".lower()
            row._filter_data = f

            name_lbl = Gtk.Label(label=f"<b>{f['name']}</b>", use_markup=True, xalign=0)
            descr_lbl = Gtk.Label(label=f["descr"], xalign=0, wrap=True)
            descr_lbl.add_css_class("dim-label")
            descr_lbl.set_max_width_chars(50)
            
            box.append(name_lbl)
            box.append(descr_lbl)
            row.set_child(box)
            self.listbox.append(row)

        # 5. Connect Search Logic
        self.search_entry.connect("search-changed", self._on_search_changed)
        self.listbox.set_filter_func(self._filter_rows)
        self.listbox.connect("row-activated", self._on_row_activated)

        # 6. Auto-focus search entry when window is ready
        self.search_entry.grab_focus()

    def _filter_rows(self, row):
        """GTK Filter Function: Returns True if row should be visible."""
        search_text = self.search_entry.get_text().lower().strip()
        if not search_text:
            return True
        return search_text in row._search_key

    def _on_search_changed(self, _):
        """Trigger the listbox to re-run the filter function."""
        self.listbox.invalidate_filter()

    def _on_row_activated(self, _, row):
        self.on_select(row._filter_data)
        self.destroy()