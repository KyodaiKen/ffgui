import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gdk, Pango
import av.format

class ContainerPickerWindow(Gtk.ApplicationWindow):
    def __init__(self, parent_window, current_val, on_select, **kwargs):
        super().__init__(**kwargs, title="Select Output Container")
        self.on_select = on_select
        self.set_default_size(450, 500)
        self.set_transient_for(parent_window)
        self.set_modal(True)
        
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

    def populate_list(self, filter_text=""):
        while child := self.lst_formats.get_first_child():
            self.lst_formats.remove(child)
        
        filter_text = filter_text.lower()
        for f in self.formats:
            if filter_text in f["id"].lower() or filter_text in f["long"].lower():
                row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
                row.props.margin_start = 6
                row.props.margin_end = 6
                row.props.margin_top = 6
                row.props.margin_bottom = 6
                
                lbl_ext = Gtk.Label(xalign=0)
                lbl_ext.set_markup(f"<b>{f["id"]}</b>")
                lbl_ext.set_width_chars(12)
                lbl_ext.set_xalign(0)
                
                lbl_name = Gtk.Label(label=f["long"], xalign=0)
                lbl_name.set_ellipsize(Pango.EllipsizeMode.END)
                
                row.append(lbl_ext)
                row.append(lbl_name)
                
                list_row = Gtk.ListBoxRow()
                list_row.set_child(row)
                list_row._data = f["id"] # Store internal ID
                self.lst_formats.append(list_row)

    def on_search_changed(self, entry):
        self.populate_list(entry.get_text())

    def on_ok_clicked(self):
        row = self.lst_formats.get_selected_row()
        if row:
            self.on_select(row._data)
            self.destroy()