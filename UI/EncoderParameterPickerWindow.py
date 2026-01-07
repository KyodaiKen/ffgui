import gi
import yaml
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Pango

class EncoderParameterPickerWindow(Gtk.Window):
    def __init__(self, parent_window, codec, on_select):
        super().__init__(title=f"Encoder Options: {codec}", transient_for=parent_window, modal=True)
        self.set_default_size(450, 550)
        self.on_select = on_select
        self.codec = codec

        # 1. Load the structured YAML data
        self.codec_params = {}
        try:
            # Adjust path if your parameters.yaml is located elsewhere
            with open("./codecs/parameters.yaml", "r") as f:
                full_data = yaml.safe_load(f)
                self.codec_params = full_data.get(codec, {}).get("parameters", {})
        except Exception as e:
            print(f"Error loading parameters.yaml: {e}")

        # 2. UI Setup: HeaderBar with SearchEntry
        hb = Gtk.HeaderBar()
        self.set_titlebar(hb)
        
        self.search_entry = Gtk.SearchEntry(placeholder_text=f"Search {codec} options...")
        self.search_entry.connect("search-changed", self.on_search_changed)
        hb.set_title_widget(self.search_entry)

        # 3. Main Layout
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_child(main_box)

        self.lst_params = Gtk.ListBox()
        self.lst_params.add_css_class("boxed-list")
        self.lst_params.connect("row-activated", self.on_row_activated)
        
        scroll = Gtk.ScrolledWindow(vexpand=True)
        scroll.set_margin_top(6)
        scroll.set_margin_start(6)
        scroll.set_margin_end(6)
        scroll.set_margin_bottom(6)
        scroll.set_child(self.lst_params)
        main_box.append(scroll)

        # Initial population
        self.populate_list()

    def populate_list(self, filter_text=""):
        # Clear existing rows
        while child := self.lst_params.get_first_child():
            self.lst_params.remove(child)
        
        if not self.codec_params:
            empty_lbl = Gtk.Label(label=f"No schema found for '{self.codec}'")
            empty_lbl.set_margin_top(20)
            self.lst_params.append(empty_lbl)
            return

        # Filter and sort by Label or Key
        search_term = filter_text.lower()
        sorted_keys = sorted(self.codec_params.keys())

        for key in sorted_keys:
            info = self.codec_params[key]
            label = info.get('label', key)
            
            # Match against key OR human-readable label
            if not search_term or search_term in key.lower() or search_term in label.lower():
                row = Gtk.ListBoxRow()
                box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
                box.set_margin_top(6)
                box.set_margin_start(6)
                box.set_margin_end(6)
                box.set_margin_bottom(6)
                
                lbl_title = Gtk.Label(label=f"<b>{label}</b>", use_markup=True, xalign=0)
                lbl_subtitle = Gtk.Label(label=f"Flag: -{key}", xalign=0)
                lbl_subtitle.add_css_class("caption")
                
                # If there's a help string or long description, show it
                help_text = info.get('help', "")
                if help_text:
                    lbl_help = Gtk.Label(label=help_text, xalign=0)
                    lbl_help.add_css_class("caption")
                    lbl_help.set_wrap(True)
                    box.append(lbl_help)

                box.append(lbl_title)
                box.append(lbl_subtitle)
                
                row.set_child(box)
                row._key = key
                row._schema = info
                self.lst_params.append(row)

    def on_search_changed(self, entry):
        self.populate_list(entry.get_text())

    def on_row_activated(self, lb, row):
        # Safety check for the "No schema found" label row
        if hasattr(row, "_key"):
            self.on_select(row._key, row._schema)
            self.destroy()