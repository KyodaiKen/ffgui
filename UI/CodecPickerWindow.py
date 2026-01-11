import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Pango

class CodecPickerWindow(Gtk.ApplicationWindow):
    def __init__(self, parent_window, codec_type, on_select, **kwargs):
        super().__init__(**kwargs, title=f"Select {codec_type.capitalize()} Codec")
        self.on_select = on_select
        self.codec_type = codec_type # 'video', 'audio', 'subtitle', or 'data'
        
        self.set_default_size(450, 500)
        self.set_transient_for(parent_window)
        self.set_modal(True)
        
        # Header Search
        hb = Gtk.HeaderBar()
        self.set_titlebar(hb)
        self.search_entry = Gtk.SearchEntry(placeholder_text=f"Search {codec_type} codec...")
        self.search_entry.connect("search-changed", self.on_search_changed)
        self.search_entry.connect("activate", lambda _: self.on_ok_clicked())
        hb.set_title_widget(self.search_entry)

        # Layout
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        main_box.props.margin_start = 6
        main_box.props.margin_end = 6
        main_box.props.margin_top = 6
        main_box.props.margin_bottom = 6
        self.set_child(main_box)

        self.lst_codecs = Gtk.ListBox()
        self.lst_codecs.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.lst_codecs.set_activate_on_single_click(False)
        self.lst_codecs.connect("row-activated", lambda *_: self.on_ok_clicked())
        
        scroll = Gtk.ScrolledWindow(vexpand=True)
        scroll.set_child(self.lst_codecs)
        main_box.append(scroll)

        self.btn_select = Gtk.Button(label="Select Codec")
        self.btn_select.add_css_class("suggested-action")
        self.btn_select.connect("clicked", lambda _: self.on_ok_clicked())
        main_box.append(self.btn_select)

        # Fetch codecs from PyAV
        self.codecs = self.get_filtered_codecs()
        self.populate_list()
        self.search_entry.grab_focus()

    def get_filtered_codecs(self):
        filtered = []

        # Access the application instance to get the cached JSON data
        app = Gtk.Application.get_default()
        if not app or not hasattr(app, 'ffmpeg_data'):
            return filtered

        # Get the codec list from your JSON (e.g., negative.json and positive.json)
        codecs_list = app.ffmpeg_data.get('codecs', [])

        for codec in codecs_list:
            flags = codec.get('flags', {})
            # Match only encoders and the correct stream type (video/audio)
            if flags.get('encoder') and flags.get(self.codec_type):
                filtered.append({
                    "id": codec.get("name"),
                    "long": codec.get("descr") # Use 'descr' from your JSON
                })

        # Always add the copy option
        filtered.append({
            "id": "copy",
            "long": "Copy (no transcoding)"
        })
        return filtered

    def populate_list(self, filter_text=""):
        while child := self.lst_codecs.get_first_child():
            self.lst_codecs.remove(child)
        
        filter_text = filter_text.lower()
        for c in self.codecs:
            if filter_text in c["id"].lower() or filter_text in c["long"].lower():
                row_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)

                top_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
                
                lbl_name = Gtk.Label(xalign=0)
                lbl_name.set_markup(f"<b>{c["id"]}</b>")
                lbl_name.set_width_chars(20)
                
                lbl_long = Gtk.Label(label=c["long"], xalign=0)
                lbl_long.set_ellipsize(Pango.EllipsizeMode.END)
                
                top_hbox.append(lbl_name)
                top_hbox.append(lbl_long)
                row_vbox.append(top_hbox)
                
                list_row = Gtk.ListBoxRow()
                list_row.set_child(row_vbox)
                list_row._data = c["id"]
                self.lst_codecs.append(list_row)

    def on_search_changed(self, entry):
        self.populate_list(entry.get_text())

    def on_ok_clicked(self):
        row = self.lst_codecs.get_selected_row()
        if row:
            self.on_select(row._data)
            self.destroy()
