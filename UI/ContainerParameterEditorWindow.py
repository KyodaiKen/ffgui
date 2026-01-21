import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Pango

from UI.SinglePickerWindow import SinglePickerWindow
from UI.FlagsPickerWindow import FlagsPickerWindow
from UI.Builder import Builder

class ContainerParameterEditorWindow(Gtk.ApplicationWindow):
    def __init__(self, parent_window, job_data, on_save_callback=None, **kwargs):
        super().__init__(**kwargs, title="Container Parameters")
        
        self.app = Gtk.Application.get_default()
        self.job_data = job_data
        self.on_save_callback = on_save_callback
        
        # Get the currently selected container name (e.g., 'mkv', 'mp4')
        if hasattr(parent_window, "selected_container"):
            self.container_name = parent_window.selected_container
        else:
            self.container_name = ""

        self.set_default_size(500, 400)
        self.set_transient_for(parent_window)
        self.set_modal(True)

        self._build_ui()
        self._load_existing_parameters()

    def _build_ui(self):
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12, margin_start=12, margin_end=12, margin_top=12, margin_bottom=12)
        self.set_child(main_box)

        # Header with Add Button
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        lbl_title = Gtk.Label(xalign=0, hexpand=True)
        lbl_title.set_markup(f"<b>Parameters for {self.container_name.upper()}</b>")
        
        btn_add = Gtk.Button(icon_name="list-add-symbolic")
        btn_add.add_css_class("flat")
        btn_add.connect("clicked", self.on_add_param_clicked)
        
        header.append(lbl_title)
        header.append(btn_add)
        main_box.append(header)

        # Scrolled List of parameters
        scroll = Gtk.ScrolledWindow(vexpand=True, has_frame=True)
        self.lst_params = Gtk.ListBox()
        self.lst_params.add_css_class("boxed-list")
        scroll.set_child(self.lst_params)
        main_box.append(scroll)

        # Footer Actions
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        btn_box.set_halign(Gtk.Align.END)
        
        btn_cancel = Gtk.Button(label="Cancel")
        btn_cancel.connect("clicked", lambda _: self.destroy())
        
        btn_save = Gtk.Button(label="Apply Changes")
        btn_save.add_css_class("suggested-action")
        btn_save.connect("clicked", self.on_save_clicked)
        
        btn_box.append(btn_cancel)
        btn_box.append(btn_save)
        main_box.append(btn_box)

    def _get_format_schema_dict(self):
        """Finds the target format in ffmpeg_data and converts its parameters list to a dict."""
        formats = getattr(self.app, 'ffmpeg_data', {}).get('formats', [])
        # Find the schema for the active container
        fmt_obj = next((f for f in formats if f.get('name') == self.container_name), None)
        
        if not fmt_obj:
            return {}

        # Convert list of param objects to a dict keyed by name for ParameterPickerWindow
        return {p['name']: p for p in fmt_obj.get('parameters', [])}

    def _load_existing_parameters(self):
        """Populates the list with parameters currently in the job data."""
        # job_data['output']['container_parameters'] is expected to be a list of {'name': x, 'value': y}
        current_params = self.job_data.get("output", {}).get("container_parameters", [])
        schema_dict = self._get_format_schema_dict()

        for p_item in current_params:
            name = p_item.get("name")
            value = p_item.get("value")
            schema = schema_dict.get(name)
            self.add_row_to_list(name, value, schema)

    def add_row_to_list(self, key, value, schema):
        row_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True, spacing=6, margin_bottom=2, margin_end=6, margin_start=6, margin_top=2)
        
        lbl_key = Gtk.Label(label=key, xalign=0, width_request=120)
        val_widget = Builder.build_value_widget(self, key, value, schema)
        btn_del = Gtk.Button(icon_name="user-trash-symbolic")

        row_box.append(lbl_key)
        row_box.append(val_widget)
        row_box.append(btn_del)

        row = Gtk.ListBoxRow(child=row_box)
        row._key = key
        row._val_widget = val_widget

        btn_del.connect("clicked", lambda _: self.lst_params.remove(row))
        self.lst_params.append(row)

    def _update_flag_button_label(self, btn):
        """Updates the MenuButton text to show selected flags."""
        active = [name for name, cb in btn._check_buttons.items() if cb.get_active()]
        if not active:
            btn.set_label("None selected")
        elif len(active) <= 2:
            btn.set_label("+".join(active))
        else:
            btn.set_label(f"{len(active)} flags selected")

    def on_add_param_clicked(self, _):
        schema_dict = self._get_format_schema_dict()
        
        def on_selected(param):
            # Check if already in list to avoid duplicates
            existing = [r._key for r in self._get_all_rows()]
            name = param.get("name", "")
            if name not in existing:
                self.add_row_to_list(name, None, param)

        plist = list(schema_dict.values())
        plist.sort(key=lambda x: (x['name'].lower()))

        picker = SinglePickerWindow(
            parent_window = self,
            options = plist,
            strings = {
                "title": f"Select a container format parameter",
                "placeholder_text": "Search for a container format parameter..."
            },
            item_filter = None,
            on_select = on_selected
        )

        picker.present()

    def _get_all_rows(self):
        rows = []
        child = self.lst_params.get_first_child()
        while child:
            if isinstance(child, Gtk.ListBoxRow):
                rows.append(child)
            child = child.get_next_sibling()
        return rows

    def on_save_clicked(self, _):
        updated_params = []
        for row in self._get_all_rows():
            val = Builder.extract_widget_value(row._val_widget)
            updated_params.append({"name": row._key, "value": val})

        if self.on_save_callback:
            self.on_save_callback(updated_params)
        else:
            # Save back to the job model directly when there is no callback function set
            self.job_data["output"]["container_parameters"] = updated_params
        
        self.destroy()
