import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Pango

class EncoderParameterPickerWindow(Gtk.ApplicationWindow):
    def __init__(self, parent_window, codec_name, schema_data, on_select, **kwargs):
        super().__init__(**kwargs, title=f"Options for {codec_name}")
        self.on_select = on_select
        self.set_default_size(450, 500)
        self.set_transient_for(parent_window)
        self.set_modal(True)

        self.params = []
        # schema_data here is the 'parameters' dict for the specific codec
        if isinstance(schema_data, dict):
            for key, info in schema_data.items():
                self.params.append({
                    "name": key,
                    "label": info.get("label", key),
                    "help": info.get("help", "No description available"),
                    "type": info.get("type", "string"),
                    "schema": info
                })

        # UI Setup
        hb = Gtk.HeaderBar()
        self.set_titlebar(hb)
        self.search_entry = Gtk.SearchEntry(placeholder_text="Filter options...")
        self.search_entry.connect("search-changed", self.on_search_changed)
        hb.set_title_widget(self.search_entry)

        self.lst_params = Gtk.ListBox()
        self.lst_params.add_css_class("boxed-list")
        self.lst_params.connect("row-activated", self.on_row_activated)

        scroll = Gtk.ScrolledWindow(vexpand=True)
        scroll.set_child(self.lst_params)
        self.set_child(scroll)

        self.populate_list()

    def populate_list(self, filter_text=""):
        while child := self.lst_params.get_first_child():
            self.lst_params.remove(child)

        for p in sorted(self.params, key=lambda x: x['name']):
            if not filter_text or filter_text.lower() in p['name'].lower() or filter_text.lower() in p['help'].lower():
                row = Gtk.ListBoxRow()
                box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4, margin_top=8, margin_bottom=8, margin_start=12, margin_end=12)

                lbl_key = Gtk.Label(label=f"<b>{p['name']}</b>", use_markup=True, xalign=0)
                lbl_help = Gtk.Label(label=p['help'], xalign=0)
                lbl_help.add_css_class("caption")
                lbl_help.set_wrap(True)

                box.append(lbl_key)
                box.append(lbl_help)
                row.set_child(box)
                row._data = p
                self.lst_params.append(row)

    def on_search_changed(self, entry):
        self.populate_list(entry.get_text())

    def on_row_activated(self, lb, row):
        self.on_select(row._data['name'], row._data['schema'])
        self.destroy()
