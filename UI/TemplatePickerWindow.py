import gi
import pathlib
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gdk, Gio, Pango
from UI.TemplateEditorWindow import TemplateEditorWindow
from UI.Icons import Icons
from Models.TemplateDataModel import TemplateDataModel

class TemplatePickerWindow(Gtk.ApplicationWindow):
    def __init__(self, parent_window, current_val, stream_type, on_select, **kwargs):
        super().__init__(**kwargs, title="Select Transcoding Template")
        self.current_val = current_val
        self.target_type = stream_type
        self.on_select = on_select
        self.app = Gtk.Application.get_default()

        # Window Configuration
        self.set_default_size(600, 500)
        self.set_size_request(600, 300)
        self.set_transient_for(parent_window)
        self.set_modal(True)

        # Header with Search
        hb = Gtk.HeaderBar()
        self.set_titlebar(hb)
        self.search_entry = Gtk.SearchEntry(placeholder_text="Search templates...")
        self.search_entry.connect("search-changed", lambda e: self.populate_list(e.get_text()))
        hb.set_title_widget(self.search_entry)

        # Main Layout
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        main_box.props.margin_start = 6
        main_box.props.margin_end = 6
        main_box.props.margin_top = 6
        main_box.props.margin_bottom = 6
        self.set_child(main_box)

        # List of Templates
        self.lst_templates = Gtk.ListBox()
        self.lst_templates.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.lst_templates.add_css_class("boxed-list")
        self.lst_templates.set_activate_on_single_click(False)
        self.lst_templates.connect("row-activated", lambda *_: self.on_ok_clicked())
        self.lst_templates.connect("selected-rows-changed", self.on_selection_changed)
        
        scroll = Gtk.ScrolledWindow(vexpand=True)
        scroll.set_child(self.lst_templates)
        main_box.append(scroll)

        # Bottom Buttons
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        main_box.append(btn_box)

        self.btn_new = Gtk.Button(label="Create New Template", hexpand=True)
        self.btn_new.add_css_class("text-button") # Subtle look
        self.btn_new.connect("clicked", self.on_new_template_clicked)
        btn_box.append(self.btn_new)

        self.btn_clone = Gtk.Button(label="Clone Template", hexpand=True)
        self.btn_clone.add_css_class("text-button") # Subtle look
        self.btn_clone.connect("clicked", self.on_clone_template_clicked)
        btn_box.append(self.btn_clone)

        self.btn_select = Gtk.Button(label="Apply Template")
        self.btn_select.add_css_class("suggested-action")
        self.btn_select.connect("clicked", lambda _: self.on_ok_clicked())
        btn_box.append(self.btn_select)

        self.btn_select.set_sensitive(False)
        self.btn_clone.set_sensitive(False)

        # Initial Load
        self.templates = []
        self.refresh_data()
        self.search_entry.grab_focus()

    def refresh_data(self):
        """Fetches fresh data from the model and repopulates."""
        # Pass self.app here to fix the TypeError
        self.templates = TemplateDataModel.get_templates_by_type(self.app, self.target_type)
        self.populate_list(self.search_entry.get_text())

    def populate_list(self, filter_text=""):
        while child := self.lst_templates.get_first_child():
            self.lst_templates.remove(child)
        
        filter_text = filter_text.lower()
        for t in self.templates:
            if filter_text in t["name"].lower():
                self.lst_templates.append(self._create_row(t))

    def _create_row(self, t):
        row_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        row_box.set_margin_top(4)
        row_box.set_margin_bottom(4)

        # 1. Type Badge
        lbl_type = Gtk.Label(label=t["type"])
        lbl_type.add_css_class("caption")
        lbl_type.set_width_chars(12)
        row_box.append(lbl_type)

        # 2. Icon
        t_type = t.get("type", "unknown").lower()
        icon_name = Icons.get_icon_for_type(t_type)
        img_type = Gtk.Image.new_from_icon_name(icon_name)
        img_type.set_tooltip_text(f"Type: {t_type.capitalize()}")
        row_box.append(img_type)

        # 3. Name + Read-only icon
        name_box = Gtk.Box(spacing=6, hexpand=True)
        lbl_name = Gtk.Label(label=f"<b>{t['name']}</b>", use_markup=True, xalign=0)
        name_box.append(lbl_name)
        
        if t.get("readonly"):
            img_lock = Gtk.Image.new_from_icon_name("changes-prevent-symbolic")
            img_lock.set_tooltip_text("System Template (Read-Only)")
            name_box.append(img_lock)
        
        row_box.append(name_box)

        # 4. Origin
        lbl_origin = Gtk.Label(label=t["origin"])
        lbl_origin.add_css_class("dim-label")
        row_box.append(lbl_origin)

        # 5. Action Buttons (Edit)
        btn_edit = Gtk.Button(icon_name="document-edit-symbolic")
        # In Picker, we usually allow editing user templates but disable for System
        if t.get("readonly"):
            btn_edit.set_sensitive(False)
            btn_edit.set_tooltip_text("System templates cannot be edited directly")
        else:
            btn_edit.connect("clicked", lambda *_: self.on_edit_template(t))
        btn_edit.props.margin_end = 24
        row_box.append(btn_edit)

        # --- CRITICAL DATA TAGS ---
        list_row = Gtk.ListBoxRow(child=row_box)
        list_row._template_name = t['name']
        list_row._template_path = t['path']
        
        return list_row

    # New handler:
    def on_selection_changed(self, _):
        has_selection = self.lst_templates.get_selected_row() is not None
        self.btn_select.set_sensitive(has_selection)
        self.btn_clone.set_sensitive(has_selection)

    def on_new_template_clicked(self, _):
        new_template = TemplateDataModel.create_empty_template(self.target_type)
        editor = TemplateEditorWindow(
            parent_window=self, 
            template=new_template,
            on_save_callback=self.on_template_saved_and_pick,
            locked_type=self.target_type
        )
        editor.present()

    def on_clone_template_clicked(self, _):
        row = self.lst_templates.get_selected_row()
        
        # 1. If no row is selected, show an alert and exit
        if not row:
            alert = Gtk.AlertDialog(
                message="No template selected",
                detail="Please select a template from the list to clone it."
            )
            alert.show(self)
            return

        # 2. Find the template data matching the row's tagged path
        selected = next((t for t in self.templates if t["path"] == row._template_path), None)

        if selected:
            # We pass clone_mode=True so the Editor handles naming (e.g., adding '_copy')
            editor = TemplateEditorWindow(
                parent_window=self, 
                template=selected, 
                on_save_callback=self.on_template_saved_and_pick,
                clone_mode=True
            )
            editor.present()

    def on_template_saved_and_pick(self, template_name):
        self.refresh_data()
        
        # Auto-select the newly created template
        row = self.lst_templates.get_first_child()
        while row:
            if hasattr(row, "_template_name") and row._template_name == template_name:
                self.lst_templates.select_row(row)
                self.on_ok_clicked()
                break
            row = row.get_next_sibling()

    def on_ok_clicked(self):
        row = self.lst_templates.get_selected_row()
        if row:
            self.on_select(row._template_name)
            self.destroy()

    def on_edit_template(self, template):
        win = TemplateEditorWindow(
            parent_window=self, 
            template=template,
            on_save_callback=lambda _: self.refresh_data(),
            locked_type=self.target_type
        )
        win.present()

    def on_row_right_clicked(self, gesture, n_press, x, y, row):
        # Select the row being right-clicked
        self.lst_templates.select_row(row)
        
        # Create the Popover Menu
        menu_model = Gio.Menu.new()
        menu_model.append("Open Containing Folder", "win.open_folder")
        menu_model.append("Edit YAML File", "win.edit_yaml")

        popover = Gtk.PopoverMenu.new_from_model(menu_model)
        popover.set_parent(row)
        popover.set_pointing_to(Gdk.Rectangle()) # Points to the mouse location

        rect = Gdk.Rectangle()
        rect.x = int(x)
        rect.y = int(y)
        rect.width = 1
        rect.height = 1
        popover.set_pointing_to(rect)
        
        # Define the actions
        action_group = Gio.SimpleActionGroup.new()
        
        # Action: Open Folder
        act_open = Gio.SimpleAction.new("open_folder", None)
        act_open.connect("activate", lambda *_: self.open_path(row._template_path, folder_only=True))
        action_group.add_action(act_open)

        # Action: Edit YAML
        act_edit = Gio.SimpleAction.new("edit_yaml", None)
        act_edit.connect("activate", lambda *_: self.open_path(row._template_path, folder_only=False))
        action_group.add_action(act_edit)

        row.insert_action_group("win", action_group)
        popover.popup()

    def open_path(self, path_str, folder_only=False):
        path = pathlib.Path(path_str).resolve()
        
        # Check if file exists before trying to open it
        if not path.exists():
            self.show_error_dialog(f"The file '{path.name}' no longer exists.")
            self.templates = self.discover_templates() # Refresh list
            self.populate_list(self.search_entry.get_text())
            return

        uri = path.parent.as_uri() if folder_only else path.as_uri()
        try:
            Gio.AppInfo.launch_default_for_uri(uri, None)
        except Exception as e:
            print(f"Launch failed: {e}")

    def show_error_dialog(self, message):
        """Simple feedback for missing files"""
        dialog = Gtk.AlertDialog(message=message)
        dialog.show(self)