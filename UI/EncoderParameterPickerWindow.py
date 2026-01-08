import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Pango

class EncoderParameterPickerWindow(Gtk.ApplicationWindow):
    # Added stream_type to the arguments
    def __init__(self, parent_window, codec_name, stream_type, schema_data, on_select, **kwargs):
        super().__init__(**kwargs, title=f"Options for {codec_name}")
        self.on_select = on_select
        self.set_default_size(450, 600)
        self.set_transient_for(parent_window)
        self.set_modal(True)

        self.params = []

        # Safely get the application instance
        app = Gtk.Application.get_default()
        if not app or not hasattr(app, 'ffmpeg_data'):
            return

        # app.ffmpeg_data['globals'] is already the list of groups from 'data' in globals.json
        groups = app.ffmpeg_data.get('globals', [])

        for group in groups:
            group_name = group.get("name", "").lower()

            # Logic to filter globals based on the current stream type
            # Note: 'av_options' is the name used in your globals.json for general context
            should_include = (group_name == "av_options") or \
                             (group_name == "video" and stream_type == "video") or \
                             (group_name == "audio" and stream_type == "audio") or \
                             (group_name == "subtitle" and stream_type == "subtitle")

            if should_include:
                for p in group.get("parameters", []):
                    self.params.append({
                        "name": p.get("name"),
                        "help": p.get("descr", "Global FFmpeg Option"), # uses 'descr' from your JSON
                        "type": p.get("type", "string"),
                        "schema": p,
                        "is_global": True
                    })

        # Add Codec-Specific (Private) Options
        params_list = []
        if isinstance(schema_data, list):
            params_list = schema_data
        elif isinstance(schema_data, dict):
            # If the dict has a 'parameters' key (like your JSON files)
            if "parameters" in schema_data:
                params_list = schema_data.get("parameters", [])
            else:
                # If the dict IS the parameters (key: info style)
                for p_name, p_info in schema_data.items():
                    if isinstance(p_info, dict):
                        # Ensure the name is included in the dict
                        p_copy = p_info.copy()
                        p_copy['name'] = p_name
                        params_list.append(p_copy)

        for p in params_list:
            # Match 'descr' from your positive.json and negative.json
            self.params.append({
                "name": p.get("name"),
                "help": p.get("descr", "Codec-specific option"),
                "type": p.get("type", "string"),
                "schema": p,
                "is_global": False
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
            if not filter_text or filter_text.lower() in p['name'].lower():
                row = Gtk.ListBoxRow()
                box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
                # Discrete margins
                box.set_margin_top(10)
                box.set_margin_bottom(10)
                box.set_margin_start(10)
                box.set_margin_end(10)

                header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
                lbl_key = Gtk.Label(xalign=0)
                lbl_key.set_markup(f"<b>{p['name']}</b>")

                type_lbl = Gtk.Label(xalign=0)
                type_text = "Global" if p.get('is_global') else "Private"
                type_lbl.set_markup(f"<span size='small' alpha='50%'>[{type_text}]</span>")

                header.append(lbl_key)
                header.append(type_lbl)

                lbl_help = Gtk.Label(label=p['help'], xalign=0)
                lbl_help.add_css_class("caption")
                lbl_help.set_wrap(True)

                box.append(header)
                box.append(lbl_help)
                row.set_child(box)
                row._data = p
                self.lst_params.append(row)

    def on_search_changed(self, entry):
        self.populate_list(entry.get_text())

    def on_row_activated(self, lb, row):
        self.on_select(row._data['name'], row._data['schema'])
        self.destroy()
