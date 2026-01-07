import gi
import pathlib
import yaml
import os
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gdk, Gio, Pango
from UI.TemplateEditorWindow import TemplateEditorWindow
from UI.Core import UICore

class TemplateManagerWindow(Gtk.ApplicationWindow):
    def __init__(self, parent_window, **kwargs):
        super().__init__(**kwargs, title="Manage Transcoding Templates")
        self.set_default_size(600, 500)
        self.set_transient_for(parent_window)
        self.set_modal(True)

        # HeaderBar with Search
        hb = Gtk.HeaderBar()
        self.set_titlebar(hb)
        self.search_entry = Gtk.SearchEntry(placeholder_text="Filter templates...")
        self.search_entry.connect("search-changed", self.on_search_changed)
        hb.set_title_widget(self.search_entry)

        # Main Layout
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        main_box.props.margin_start = 6
        main_box.props.margin_end = 6
        main_box.props.margin_top = 6
        main_box.props.margin_bottom = 6
        self.set_child(main_box)

        # ListBox
        self.lst_templates = Gtk.ListBox()
        self.lst_templates.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.lst_templates.add_css_class("boxed-list")
        
        scroll = Gtk.ScrolledWindow(vexpand=True)
        scroll.set_child(self.lst_templates)
        main_box.append(scroll)

        # Toolbar
        action_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.btn_new = Gtk.Button(label="New Template", icon_name="list-add-symbolic")
        self.btn_new.connect("clicked", self.on_new_template)
        action_box.append(self.btn_new)
        
        main_box.append(action_box)

        self.refresh_list()

    def discover_templates(self):
        paths = [pathlib.Path("./templates"), pathlib.Path.home() / ".config" / "ffgui" / "templates"]
        found = []
        for p in paths:
            if p.exists() and p.is_dir():
                for file in p.glob("*.yaml"):
                    try:
                        with open(file, 'r') as f:
                            data = yaml.safe_load(f)
                            found.append({
                                "name": file.stem,
                                "path": str(file.resolve()),
                                "type": data.get("type", "unknown").upper(),
                                "origin": "User" if ".config" in str(p) else "System",
                                "data": data
                            })
                    except: continue
        return sorted(found, key=lambda x: (x['type'], x['name'].lower()))

    def populate_ui(self, filter_text=""):
        while child := self.lst_templates.get_first_child():
            self.lst_templates.remove(child)
        
        templates = self.discover_templates()
        for t in templates:
            if filter_text.lower() in t["name"].lower():
                row_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

                # Type Badge
                lbl_type = Gtk.Label(label=t["type"])
                lbl_type.add_css_class("caption")
                lbl_type.set_width_chars(8)
                row_box.append(lbl_type)

                t_type = t.get("type", "unknown").lower()
                icon_name = UICore.get_icon_for_type(t_type)
                img_type = Gtk.Image.new_from_icon_name(icon_name)
                img_type.set_tooltip_text(f"Type: {t_type.capitalize()}")
                row_box.append(img_type)

                # Name
                lbl_name = Gtk.Label(label=f"<b>{t['name']}</b>", use_markup=True, xalign=0, hexpand=True)
                row_box.append(lbl_name)

                # Origin
                lbl_origin = Gtk.Label(label=t["origin"])
                lbl_origin.add_css_class("dim-label")
                row_box.append(lbl_origin)

                # Action Buttons
                btn_edit = Gtk.Button(icon_name="document-edit-symbolic")
                btn_edit.connect("clicked", self.on_edit_clicked, t)
                row_box.append(btn_edit)

                btn_rename = Gtk.Button(icon_name="insert-text-symbolic")
                btn_rename.connect("clicked", self.on_rename_clicked, t)
                btn_rename.props.margin_end = 24
                row_box.append(btn_rename)

                list_row = Gtk.ListBoxRow()
                list_row.set_child(row_box)
                self.lst_templates.append(list_row)

    def on_search_changed(self, entry):
        self.populate_ui(entry.get_text())

    def refresh_list(self):
        self.populate_ui(self.search_entry.get_text())

    def on_new_template(self, _):
        # We can prompt for type first or default to Video in Editor
        win = TemplateEditorWindow(self, template=None)
        win.present()

    def on_edit_clicked(self, _, template):
        win = TemplateEditorWindow(self, template=template)
        win.present()

    def on_rename_clicked(self, _, template):
        # Create a simple Entry dialog (GTK4 style)
        self.rename_dialog = Gtk.FileDialog(title=f"Rename {template['name']}")
        
        # Note: Since GTK4 FileDialog is for picking, we use a simple Gtk.Window 
        # as an 'input prompt' or Gtk.Entry inside an AlertDialog.
        # For brevity, let's use an Entry row logic:
        msg = Gtk.Label(label=f"New name for '{template['name']}':")
        entry = Gtk.Entry(text=template['name'])
        
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        content.append(msg)
        content.append(entry)

        alert = Gtk.MessageDialog(
            transient_for=self,
            modal=True,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.OK_CANCEL,
            text="Rename Template"
        )
        alert.get_content_area().append(content)
        
        def response(dialog, response_id):
            if response_id == Gtk.ResponseType.OK:
                new_name = entry.get_text().strip()
                if new_name and new_name != template['name']:
                    old_path = pathlib.Path(template['path'])
                    new_path = old_path.with_name(f"{new_name}.yaml")
                    try:
                        os.rename(old_path, new_path)
                        self.refresh_list()
                    except Exception as e:
                        print(f"Rename failed: {e}")
            dialog.destroy()

        alert.connect("response", response)
        alert.present()