import gi
import pathlib
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gdk, Gio, Pango
import yaml
from UI.TemplateEditorWindow import TemplateEditorWindow
from UI.Core import UICore

class TemplatePickerWindow(Gtk.ApplicationWindow):
    def __init__(self, parent_window, current_val, stream_type, on_select, **kwargs):
        super().__init__(**kwargs, title="Select Transcoding Template")
        self.current_val = current_val
        self.target_type = stream_type
        self.on_select = on_select
        self.set_default_size(600, 500)
        self.set_size_request(600, 300)
        self.set_transient_for(parent_window)
        self.set_modal(True)

        # 1. Header with Search
        hb = Gtk.HeaderBar()
        self.set_titlebar(hb)
        self.search_entry = Gtk.SearchEntry(placeholder_text="Search templates...")
        self.search_entry.connect("search-changed", self.on_search_changed)
        hb.set_title_widget(self.search_entry)

        # 2. Main Layout
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        main_box.props.margin_start = 12
        main_box.props.margin_end = 12
        main_box.props.margin_top = 12
        main_box.props.margin_bottom = 12
        self.set_child(main_box)

        # List of Templates
        self.lst_templates = Gtk.ListBox()
        self.lst_templates.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.lst_templates.add_css_class("boxed-list")
        self.lst_templates.set_activate_on_single_click(False)
        self.lst_templates.connect("row-activated", lambda *_: self.on_ok_clicked())
        
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

        self.btn_clone = Gtk.Button(label="CloneTemplate", hexpand=True)
        self.btn_clone.add_css_class("text-button") # Subtle look
        self.btn_clone.connect("clicked", self.on_clone_template_clicked)
        btn_box.append(self.btn_clone)

        self.btn_select = Gtk.Button(label="Apply Template")
        self.btn_select.add_css_class("suggested-action")
        self.btn_select.connect("clicked", lambda _: self.on_ok_clicked())
        btn_box.append(self.btn_select)

        # Load Data
        self.templates = self.discover_templates()
        self.populate_list()
        self.search_entry.grab_focus()

    def discover_templates(self):
        paths_to_scan = [
            pathlib.Path("./templates"),
            pathlib.Path.home() / ".config" / "ffgui" / "templates"
        ]
        
        found_templates = []
        for p in paths_to_scan:
            if p.exists() and p.is_dir():
                for file in p.glob("*.yaml"):
                    try:
                        with open(file, 'r') as f:
                            data = yaml.safe_load(f)
                            # Only include if the template type matches the stream type
                            if data and data.get('type') == self.target_type:
                                found_templates.append({
                                    "name": file.stem,
                                    "path": str(file.resolve()),
                                    "type": data.get("type", "unknown").upper(),
                                    "origin": "User" if ".config" in str(p) else "System",
                                    "data": data
                                })
                    except Exception as e:
                        print(f"Error reading {file}: {e}")
                        
        return sorted(found_templates, key=lambda x: (x['type'], x['name'].lower()))

    def populate_list(self, filter_text=""):
        while child := self.lst_templates.get_first_child():
            self.lst_templates.remove(child)
        
        filter_text = filter_text.lower()
        for t in self.templates:
            if filter_text in t["name"].lower():
                row_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

                # Type Badge
                lbl_type = Gtk.Label(label=t["type"])
                lbl_type.add_css_class("caption")
                lbl_type.set_width_chars(12)
                row_box.append(lbl_type)

                t_type = t.get("type", "unknown").lower()
                icon_name = UICore.get_icon_for_type(t_type)
                img_type = Gtk.Image.new_from_icon_name(icon_name)
                img_type.set_tooltip_text(f"Type: {t_type.capitalize()}")
                row_box.append(img_type)

                lbl_name = Gtk.Label(label=f"<b>{t["name"]}</b>", xalign=0, hexpand=True, use_markup=True)
                lbl_name.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
                row_box.append(lbl_name)

                lbl_origin = Gtk.Label(label=t["origin"], xalign=1)
                lbl_origin.add_css_class("dim-label")
                row_box.append(lbl_origin)

                btn_edit = Gtk.Button(icon_name="document-edit-symbolic")
                btn_edit.set_tooltip_text("Edit Template")
                btn_edit.set_margin_end(24)
                btn_edit.connect("clicked", self.on_edit_template_clicked, t)
                row_box.append(btn_edit)

                list_row = Gtk.ListBoxRow()
                list_row.set_child(row_box)
                list_row._template_path = t["path"]
                list_row._template_name = t["name"]

                gesture = Gtk.GestureClick.new()
                gesture.set_button(Gdk.BUTTON_SECONDARY) # Right click
                gesture.connect("pressed", self.on_row_right_clicked, list_row)
                list_row.add_controller(gesture)

                self.lst_templates.append(list_row)

    def on_search_changed(self, entry):
        self.populate_list(entry.get_text())

    def on_new_template_clicked(self, btn):
        # 1. Create a blank template structure
        new_template = {
            "name": "",
            "path": "",
            "origin": "User", # New templates are usually user-created
            "data": {
                "type": "video",
                "codec": "libx264",
                "parameters": {"options": {}}
            }
        }
        
        # 2. Open the Editor Window
        # We pass self.on_template_saved_and_pick as a custom callback
        editor = TemplateEditorWindow(
            parent_window=self, 
            template=new_template,
            on_save_callback=self.on_template_saved_and_pick,
            locked_type=self.target_type
        )
        editor.present()

    def on_clone_template_clicked(self, btn):
        # 1. Get the currently selected row
        row = self.lst_templates.get_selected_row()
        
        if not row:
            self.show_error_dialog("Please select a template to clone first.")
            return

        # 2. Find the corresponding template data from our list
        # We use the path stored in the row as a unique identifier
        selected_path = row._template_path
        original_template = next((t for t in self.templates if t["path"] == selected_path), None)

        if not original_template:
            self.show_error_dialog("Could not find the source template data.")
            return

        # 3. Open the Editor Window in clone_mode
        # We don't need to manually copy here because TemplateEditorWindow 
        # calls copy.deepcopy(template) in its constructor.
        editor = TemplateEditorWindow(
            parent_window=self, 
            template=original_template,
            on_save_callback=self.on_template_saved_and_pick,
            locked_type=self.target_type,
            clone_mode=True
        )
        editor.present()

    def on_template_saved_and_pick(self, template_name):
        self.templates = self.discover_templates()
        self.populate_list()
        
        # Automatically select the new template
        # We search through our ListBox for the row matching the new name
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

    def on_edit_template_clicked(self, button, template):
        """Opens the TemplateSetupWindow for the selected template"""
        print(f"Opening TemplateSetupWindow for: {template['name']}")
        win = TemplateEditorWindow(
            parent_window=self, 
            template=template,
            on_save_callback=self.on_template_saved_and_pick,
            locked_type=self.target_type
        )
        win.present()

    def show_error_dialog(self, message):
        """Simple feedback for missing files"""
        dialog = Gtk.AlertDialog(message=message)
        dialog.show(self)