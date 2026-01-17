import gi
import pathlib
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gdk, Gio, Pango
from UI.TemplateEditorWindow import TemplateEditorWindow
from UI.Icons import Icons
from Models.TemplateDataModel import TemplateDataModel

class TemplateManagerWindow(Gtk.ApplicationWindow):
    def __init__(self, parent_window, picker_mode=False, stream_type=None, on_select=None, **kwargs):
        super().__init__(**kwargs, title="Select Template" if picker_mode else "Manage Templates")
        self.app = Gtk.Application.get_default()
        self.picker_mode = picker_mode
        self.target_type = stream_type # e.g., 'video' or 'audio'
        self.on_select = on_select     # Callback for picker mode
        
        # Window Config
        self.set_default_size(750, 550)
        self.set_transient_for(parent_window)
        self.set_modal(True)

        # Header with Search
        hb = Gtk.HeaderBar()
        self.set_titlebar(hb)
        self.search_entry = Gtk.SearchEntry(placeholder_text="Filter templates...")
        self.search_entry.connect("search-changed", lambda e: self.populate_ui(e.get_text()))
        hb.set_title_widget(self.search_entry)

        # Main Layout
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8, margin_bottom=10, margin_end=10, margin_start=10, margin_top=10)
        self.set_child(main_box)

        # ListBox
        self.lst_templates = Gtk.ListBox()
        self.lst_templates.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.lst_templates.add_css_class("boxed-list")
        self.lst_templates.connect("selected-rows-changed", self.on_selection_changed)

        scroll = Gtk.ScrolledWindow(vexpand=True)
        scroll.set_child(self.lst_templates)
        main_box.append(scroll)

        # Toolbar / Action Box
        action_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        main_box.append(action_box)

        self.btn_new = Gtk.Button(label="New Template", icon_name="list-add-symbolic")
        self.btn_new.set_tooltip_text("Create a brand new transcoding template")
        self.btn_new.connect("clicked", self.on_new_template)
        action_box.append(self.btn_new)

        self.btn_clone = Gtk.Button(label="Clone", icon_name="edit-copy-symbolic")
        self.btn_clone.set_tooltip_text("Create a copy of the selected template")
        self.btn_clone.set_sensitive(False)
        self.btn_clone.connect("clicked", self.on_clone_clicked)
        action_box.append(self.btn_clone)

        # Spacer to push Apply button to the right
        action_box.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True, opacity=0))

        if self.picker_mode:
            self.btn_apply = Gtk.Button(label="Apply Template")
            self.btn_apply.add_css_class("suggested-action")
            self.btn_apply.set_tooltip_text("Confirm selection and return to job setup")
            self.btn_apply.set_sensitive(False)
            self.btn_apply.connect("clicked", self.on_apply_clicked)
            action_box.append(self.btn_apply)

        self.populate_ui()

    def populate_ui(self, filter_text=""):
        while child := self.lst_templates.get_first_child():
            self.lst_templates.remove(child)
        
        # Logic: If target_type is set, filter by that type. Otherwise get all.
        if self.target_type:
            templates = TemplateDataModel.get_templates_by_type(self.app, self.target_type)
        else:
            templates = TemplateDataModel.get_all_templates(self.app)
        
        for t in templates:
            if not filter_text or filter_text.lower() in t["name"].lower():
                self.lst_templates.append(self._create_row(t))

    def _create_row(self, t):
        row_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6, margin_bottom=6, margin_end=6, margin_start=6, margin_top=6)
        
        # 1. Type Badge
        lbl_type = Gtk.Label(label=t["type"].upper())
        lbl_type.add_css_class("caption")
        lbl_type.set_width_chars(12)
        row_box.append(lbl_type)

        # 2. Icon
        icon_name = Icons.get_icon_for_type(t.get("type", "unknown").lower())
        row_box.append(Gtk.Image.new_from_icon_name(icon_name))

        # 3. Name (with Ellipsizing in the Middle)
        lbl_name = Gtk.Label(use_markup=True, xalign=0, hexpand=True)
        lbl_name.set_markup(f"<b>{t['name']}</b>")
        lbl_name.set_ellipsize(Pango.EllipsizeMode.MIDDLE) # Requirement met
        row_box.append(lbl_name)
        
        if t.get("readonly"):
            img_lock = Gtk.Image.new_from_icon_name("changes-prevent-symbolic")
            img_lock.set_tooltip_text("System Template")
            row_box.append(img_lock)

        # 4. Origin
        lbl_origin = Gtk.Label(label=t["origin"])
        lbl_origin.add_css_class("dim-label")
        row_box.append(lbl_origin)

        # 5. Buttons
        btn_edit = Gtk.Button(icon_name="document-edit-symbolic")
        btn_edit.connect("clicked", lambda *_: self.on_edit_clicked(t))
        row_box.append(btn_edit)

        # Metadata for row
        row = Gtk.ListBoxRow(child=row_box)
        row._data = t
        return row

    def on_selection_changed(self, _):
        row = self.lst_templates.get_selected_row()
        has_selection = row is not None
        self.btn_clone.set_sensitive(has_selection)
        if self.picker_mode:
            self.btn_apply.set_sensitive(has_selection)

    def on_new_template(self, _):
        new_data = TemplateDataModel.create_empty_template(self.target_type or "video")
        win = TemplateEditorWindow(self, template=new_data, on_save_callback=lambda _: self.populate_ui())
        win.present()

    def on_clone_clicked(self, _):
        row = self.lst_templates.get_selected_row()
        if not row: return
        
        win = TemplateEditorWindow(
            self, 
            template=row._data, 
            clone_mode=True, 
            on_save_callback=lambda _: self.populate_ui()
        )
        win.present()

    def on_edit_clicked(self, template):
        is_readonly = template.get("readonly", False)
        win = TemplateEditorWindow(
            self, 
            template=template, 
            clone_mode=is_readonly, 
            on_save_callback=lambda _: self.populate_ui(),
            locked_type=self.target_type
        )
        win.present()

    def on_apply_clicked(self, _):
        row = self.lst_templates.get_selected_row()
        if row and self.on_select:
            self.on_select(row._data['name'])
            self.destroy()