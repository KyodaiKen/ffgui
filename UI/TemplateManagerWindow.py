import gi
import os
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gdk, Gio, Pango
from UI.TemplateEditorWindow import TemplateEditorWindow
from UI.Icons import Icons
from Models.TemplateDataModel import TemplateDataModel

class TemplateManagerWindow(Gtk.ApplicationWindow):
    def __init__(self, parent_window, **kwargs):
        super().__init__(**kwargs, title="Manage Transcoding Templates")
        self.set_default_size(720, 500)
        self.set_size_request(720, 500)
        self.set_transient_for(parent_window)
        self.set_modal(True)

        # --- UI Setup ---
        # HeaderBar with Search
        hb = Gtk.HeaderBar()
        self.set_titlebar(hb)
        self.search_entry = Gtk.SearchEntry(placeholder_text="Filter templates...")
        self.search_entry.connect("search-changed", lambda e: self.populate_ui(e.get_text()))
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

        self.populate_ui()

    def populate_ui(self, filter_text=""):
        while child := self.lst_templates.get_first_child():
            self.lst_templates.remove(child)
        
        # Pass self.app (the Gtk.Application instance)
        templates = TemplateDataModel.get_all_templates(Gtk.Application.get_default())
        
        for t in templates:
            if not filter_text or filter_text.lower() in t["name"].lower():
                self.lst_templates.append(self._create_row(t))

    def _create_row(self, t):
        row_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        row_box.set_margin_top(4)     # Add a tiny bit of breathing room
        row_box.set_margin_bottom(4)
        # Type Badge
        lbl_type = Gtk.Label(label=t["type"])
        lbl_type.add_css_class("caption")
        lbl_type.set_width_chars(12)
        row_box.append(lbl_type)

        t_type = t.get("type", "unknown").lower()
        icon_name = Icons.get_icon_for_type(t_type)
        img_type = Gtk.Image.new_from_icon_name(icon_name)
        img_type.set_tooltip_text(f"Type: {t_type.capitalize()}")
        row_box.append(img_type)

        # Name + Read-only icon if applicable
        name_box = Gtk.Box(spacing=6, hexpand=True)
        lbl_name = Gtk.Label(label=f"<b>{t['name']}</b>", use_markup=True, xalign=0)
        name_box.append(lbl_name)
        
        if t.get("readonly"):
            img_lock = Gtk.Image.new_from_icon_name("changes-prevent-symbolic")
            img_lock.set_tooltip_text("System Template (Read-Only)")
            name_box.append(img_lock)
        
        row_box.append(name_box)

        # Origin
        lbl_origin = Gtk.Label(label=t["origin"])
        lbl_origin.add_css_class("dim-label")
        row_box.append(lbl_origin)

        # Action Buttons
        btn_edit = Gtk.Button(icon_name="document-edit-symbolic")
        btn_edit.connect("clicked", lambda *_: self.on_edit_clicked(t))
        row_box.append(btn_edit)

        btn_rename = Gtk.Button(icon_name="insert-text-symbolic")
        # Disable rename button if the file is read-only
        btn_rename.set_sensitive(not t.get("readonly")) 
        btn_rename.connect("clicked", lambda *_: self.on_rename_clicked(t))
        btn_rename.props.margin_end = 24
        row_box.append(btn_rename)

        return Gtk.ListBoxRow(child=row_box)

    def on_new_template(self, _):
        # Use Model to generate the blank starting data
        new_data = TemplateDataModel.create_empty_template()
        win = TemplateEditorWindow(self, template=new_data, on_save_callback=lambda _: self.populate_ui())
        win.present()

    def on_edit_clicked(self, template):
        # If it's read-only, we treat it like a "Clone" so the user
        # saves a new version in their User directory instead of failing to save.
        is_readonly = template.get("readonly", False)
        
        win = TemplateEditorWindow(
            self, 
            template=template, 
            clone_mode=is_readonly, # Force clone mode for system templates
            on_save_callback=lambda _: self.populate_ui()
        )
        if is_readonly:
            win.set_title(f"Copying System Template: {template['name']}")
            
        win.present()

    def on_rename_clicked(self, template):
        entry = Gtk.Entry(text=template['name'])
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_margin_top(12)
        box.set_margin_bottom(12)
        box.append(Gtk.Label(label=f"Enter new name for '{template['name']}':"))
        box.append(entry)

        dialog = Gtk.MessageDialog(
            transient_for=self, 
            modal=True, 
            text="Rename Template", 
            buttons=Gtk.ButtonsType.OK_CANCEL
        )
        dialog.get_content_area().append(box)
        
        def on_response(d, res):
            if res == Gtk.ResponseType.OK:
                new_name = entry.get_text().strip()
                if new_name and new_name != template['name']:
                    # Call the Model to handle the file rename
                    success, msg = TemplateDataModel.rename_template(template['path'], new_name)
                    if success:
                        self.populate_ui()
                    else:
                        err = Gtk.AlertDialog(message=f"Error: {msg}")
                        err.show(self)
            d.destroy()

        dialog.connect("response", on_response)
        dialog.present()