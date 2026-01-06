import gi
gi.require_version("Gdk", "4.0")
from gi.repository import Gtk

class MetadataManagerWindow(Gtk.ApplicationWindow):
    def __init__(self, parent_window, current_metadata, on_save, **kwargs):
        super().__init__(**kwargs, title="Manage Metadata")
        self.on_save = on_save
        self.set_default_size(400, 450)
        self.set_transient_for(parent_window)
        self.set_modal(True)

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        main_box.props.margin_start = 6
        main_box.props.margin_end = 6
        main_box.props.margin_top = 6
        main_box.props.margin_bottom = 6
        self.set_child(main_box)

        # List to hold the key:value rows
        self.lst_metadata = Gtk.ListBox()
        self.lst_metadata.add_css_class("boxed-list")
        
        scroll = Gtk.ScrolledWindow(vexpand=True)
        scroll.set_child(self.lst_metadata)
        main_box.append(scroll)

        # Button box for actions
        action_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        main_box.append(action_hbox)

        btn_add = Gtk.Button(label="Add New Tag", hexpand=True)
        btn_add.connect("clicked", self.on_add_row)
        action_hbox.append(btn_add)

        # Clear All Button
        btn_clear = Gtk.Button(label="Clear All")
        btn_clear.add_css_class("destructive-action")
        btn_clear.connect("clicked", self.on_clear_all)
        action_hbox.append(btn_clear)

        # Save Button
        btn_save = Gtk.Button(label="Apply Changes")
        btn_save.add_css_class("suggested-action")
        btn_save.connect("clicked", self.on_save_clicked)
        main_box.append(btn_save)

        # Populate with existing data
        if current_metadata:
            for k, v in current_metadata.items():
                self.add_metadata_row(k, v)

    def add_metadata_row(self, key="", value=""):
        row_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        ent_key = Gtk.Entry(placeholder_text="Key", text=str(key), hexpand=True)
        ent_val = Gtk.Entry(placeholder_text="Value", text=str(value), hexpand=True)
        btn_del = Gtk.Button(icon_name="user-trash-symbolic")
        
        row_box.append(ent_key)
        row_box.append(ent_val)
        row_box.append(btn_del)
        
        list_row = Gtk.ListBoxRow()
        list_row.set_child(row_box)
        btn_del.connect("clicked", lambda _: self.lst_metadata.remove(list_row))
        self.lst_metadata.append(list_row)

    def on_add_row(self, _):
        self.add_metadata_row()

    def on_clear_all(self, _):
        # Simply remove all rows from the ListBox
        self.lst_metadata.remove_all()

    def on_save_clicked(self, _):
        new_meta = {}
        row = self.lst_metadata.get_first_child()
        while row:
            if isinstance(row, Gtk.ListBoxRow):
                box = row.get_child()
                k = box.get_first_child().get_text().strip()
                v = box.get_first_child().get_next_sibling().get_text().strip()
                if k: 
                    new_meta[k] = v
            row = row.get_next_sibling()
        self.on_save(new_meta)
        self.destroy()