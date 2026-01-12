import gi

from UI.FlagsPickerWindow import FlagsPickerWindow
from UI.PillBuilder import PillBuilder
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Pango
from UI.ParameterPickerWindow import ParameterPickerWindow

class ContainerParameterEditorWindow(Gtk.ApplicationWindow):
    def __init__(self, parent_window, job_data, on_save_callback=None, **kwargs):
        super().__init__(**kwargs, title="Container Parameters")
        
        self.app = Gtk.Application.get_default()
        self.job_data = job_data
        self.on_save_callback = on_save_callback
        
        # Get the currently selected container name (e.g., 'mkv', 'mp4')
        self.container_name = parent_window.selected_container

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

    def add_row_to_list(self, key, value=None, schema=None):
        row_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        
        lbl_key = Gtk.Label(label=key, xalign=0, width_request=120)
        val_widget = self.create_value_widget(key, value, schema)
        spacer = Gtk.Box(hexpand=True)
        btn_del = Gtk.Button(icon_name="user-trash-symbolic")
        btn_del.add_css_class("flat")

        row_box.append(lbl_key)
        row_box.append(val_widget)
        row_box.append(spacer)
        row_box.append(btn_del)

        row = Gtk.ListBoxRow(child=row_box)
        row._key = key
        row._val_widget = val_widget

        btn_del.connect("clicked", lambda _: self.lst_params.remove(row))
        self.lst_params.append(row)

    def create_value_widget(self, key, value, schema):
        if not schema:
            return Gtk.Entry(text=str(value if value is not None else ""), hexpand=True)

        p_type = str(schema.get("type", "string")).lower()
        options_list = schema.get("options", [])

        # 1. Multi-Select Flags as Pills (Gtk.FlowBox)
        if p_type == "flags":
            btn = Gtk.Button(hexpand=True)
            btn.set_valign(Gtk.Align.CENTER)
            
            # The container for the pills inside the button
            flowbox = Gtk.FlowBox(
                selection_mode=Gtk.SelectionMode.NONE,
                column_spacing=4,
                row_spacing=4,
                margin_bottom=2,
                margin_end=2,
                margin_start=2,
                margin_top=2
            )
            btn.set_child(flowbox)
            
            # Store the current state on the button object for easy extraction
            btn._current_value = value

            # Internal helper to refresh the UI
            def refresh_ui(new_values):
                btn._current_value = new_values
                
                PillBuilder.build(flowbox, new_values, no_target=True)
                
                # Show a placeholder if empty
                if not flowbox.get_first_child():
                    lbl = Gtk.Label(label="None selected")
                    lbl.add_css_class("dim-label")
                    flowbox.append(lbl)

            # Initial population
            refresh_ui(btn._current_value)

            def on_picker_clicked(_):
                strings = {
                    "title": f"Select {key}",
                    "placeholder_text": "Search flags..."
                }
                # Open the window we created earlier
                win = FlagsPickerWindow(
                    parent=self, 
                    options=options_list, 
                    current_values=btn._current_value, 
                    strings=strings, 
                    on_apply=refresh_ui
                )
                win.present()

            btn.connect("clicked", on_picker_clicked)
            return btn

        # 2. Single-Select DropDown (for non-flag options)
        if options_list and p_type != "flags":
            # ... existing DropDown logic from TemplateEditorWindow ...
            tech_values = [str(o.get('name')) for o in options_list]
            display_names = [f"{o.get('name')} ({o.get('descr')})" if o.get('descr') else str(o.get('name')) for o in options_list]
            w = Gtk.DropDown(model=Gtk.StringList.new(display_names), hexpand=True)
            w._tech_values = tech_values
            # ... (selection logic) ...
            return w

        # ... keep Numeric/Boolean/Entry logic ...
        
        # 3. Booleans (Switches)
        if p_type in ["bool", "boolean"]:
            active = str(value).lower() in ['true', '1', 'on'] if value is not None else bool(schema.get("default"))
            return Gtk.Switch(active=active, halign=Gtk.Align.START)

        # 4. Numeric (Spinners)
        if any(t in p_type for t in ["int", "integer", "float", "double"]):
            try:
                v_min = float(schema.get("min", -2147483648))
                v_max = float(schema.get("max", 2147483647))
                v_cur = float(value) if value is not None else float(schema.get("default", 0))
                
                adj = Gtk.Adjustment(value=v_cur, lower=v_min, upper=v_max, step_increment=1, page_increment=10)
                spin = Gtk.SpinButton(adjustment=adj, numeric=True)
                spin.set_digits(1 if "float" in p_type or "double" in p_type else 0)
                return spin
            except: pass

        # 5. Default (Entry)
        return Gtk.Entry(text=str(value if value is not None else ""), hexpand=True)
    
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
        
        def on_selected(name, schema):
            # Check if already in list to avoid duplicates
            existing = [r._key for r in self._get_all_rows()]
            if name not in existing:
                self.add_row_to_list(name, None, schema)

        picker = ParameterPickerWindow(self, schema_dict, on_selected)
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
            val = self.extract_widget_value(row._val_widget)
            updated_params.append({"name": row._key, "value": val})

        if self.on_save_callback:
            self.on_save_callback(updated_params)
        else:
            # Save back to the job model directly when there is no callback function set
            self.job_data["output"]["container_parameters"] = updated_params
        
        self.destroy()

    def extract_widget_value(self, w):
        """Helper to get value from widget."""
        if isinstance(w, Gtk.Button) and hasattr(w, "_current_value"):
            return w._current_value
        elif isinstance(w, Gtk.DropDown):
            if hasattr(w, "_tech_values"):
                return w._tech_values[w.get_selected()]
            return w.get_selected_item().get_string()
        elif isinstance(w, Gtk.SpinButton):
            val = w.get_value()
            return int(val) if val.is_integer() else val
        elif isinstance(w, Gtk.Switch):
            return w.get_active()
        elif isinstance(w, Gtk.Entry):
            return w.get_text()
        return ""