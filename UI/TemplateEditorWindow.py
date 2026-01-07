import gi
gi.require_version("Gdk", "4.0")
from gi.repository import Gtk, Gdk, Pango
from UI.CodecPickerWindow import CodecPickerWindow
from UI.ParameterPickerWindow import ParameterPickerWindow
from UI.Core import UICore
import copy
import yaml
from pathlib import Path

all_types = UICore.get_all_types()

class TemplateEditorWindow(Gtk.ApplicationWindow):
    def __init__(self, parent_window, template, on_save_callback=None, locked_type=None,**kwargs):
        super().__init__(**kwargs, title="Template Editor")
        self.on_save_callback = on_save_callback
        self.locked_type = locked_type
        self.selected_codec = ""

        # Set window size
        self.set_size_request(640, 480)
        self.set_default_size(1024, 700)
        self.set_transient_for(parent_window)
        self.set_modal(True)

        # Create a CSS Provider
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data("""
            .codec-tag {
                background-color: alpha(@theme_fg_color, 0.05);
                border: 1px solid mix(@theme_fg_color, @theme_bg_color, 0.8);
                border-radius: 6px;
                padding: 2px;
            }
            .codec-tag label {
                margin: 0 6px 0 0;
                font-weight: bold;
                line-height: 100%;
            }
            
            /* Neutralize the 'activatable' hover effect inside the dropdown button */
            dropdown > button > box > stack > row.activatable:hover,
            dropdown > button > box > stack > row.activatable:selected,
            dropdown > button > box > stack > row.activatable {
                background-color: transparent;
                background-image: none;
                box-shadow: none;
                outline: none;

            }
        """, -1)

        # Apply the provider to the display
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_USER
        )

        # Setup Main Layout
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        main_box.props.margin_start = 6
        main_box.props.margin_end = 6
        main_box.props.margin_top = 6
        main_box.props.margin_bottom = 6
        self.set_child(main_box)

        # Top Section: Name, Type, Codec (Your existing code)
        grid = Gtk.Grid(row_spacing=10, column_spacing=10)
        main_box.append(grid)

        grid.attach(Gtk.Label(label="Name:", halign=Gtk.Align.END), 0, 0, 1, 1)
        self.entry_name = Gtk.Entry(hexpand=True)
        grid.attach(self.entry_name, 1, 0, 1, 1)

        grid.attach(Gtk.Label(label="Type:", halign=Gtk.Align.END), 0, 1, 1, 1)
        self.combo_type = Gtk.DropDown.new_from_strings([t.capitalize() for t in all_types])
        self.combo_type.props.hexpand = False
        self.combo_type.props.halign = Gtk.Align.START
        self.combo_type.set_size_request(108,-1)
        self.combo_type.connect("notify::selected", self.on_type_changed)
        grid.attach(self.combo_type, 1, 1, 1, 1)

        grid.attach(Gtk.Label(label="Codec:", halign=Gtk.Align.END), 0, 2, 1, 1)
        self.codec_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        grid.attach(self.codec_box, 1, 2, 1, 1)

        # Separator
        main_box.append(Gtk.Separator())
        main_box.append(Gtk.Label(label="Encoder Parameters", xalign=0, margin_top=6))

        # Dual List Section
        list_container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12, vexpand=True)
        main_box.append(list_container)

        # Left Column: Global Parameters (Probed)
        col_left = self.create_list_column("Stream Options", "list-add-symbolic", self.on_add_global)
        self.lst_global = col_left._list
        list_container.append(col_left)

        # Right Column: Private Options (The 'options' dict - e.g. CRF)
        col_right = self.create_list_column("Encoder Options", "list-add-symbolic", self.on_add_private)
        self.lst_private = col_right._list
        list_container.append(col_right)

        # Create a SizeGroup for the Global Parameter buttons
        self.global_keys_group = Gtk.SizeGroup(mode=Gtk.SizeGroupMode.HORIZONTAL)
        
        # (Optional) If you want the custom "key" entries on the right to match too:
        self.private_keys_group = Gtk.SizeGroup(mode=Gtk.SizeGroupMode.HORIZONTAL)

        # Footer
        btn_save = Gtk.Button(label="Save Template")
        btn_save.add_css_class("suggested-action")
        btn_save.props.hexpand = False
        btn_save.props.halign = Gtk.Align.END
        btn_save.connect("clicked", self.on_save_clicked)
        main_box.append(btn_save)

        # Load existing data
        if template:
            self.template = copy.deepcopy(template)
        else:
            self.template = {
                "name": "",
                "path": "",
                "origin": "System",
                "data": {
                    "type": "video",
                    "codec": "libx264",
                    "parameters": {"options": {}}
                }
            }
        
        # 2. Sync selected_codec from the now-existing self.template
        self.selected_codec = self.template['data']['codec']

        # 3. Now load the data into the UI (this will trigger signals safely)
        if template:
            self.load_structured_template(self.template)
        
        self.update_codec_ui()

    def create_list_column(self, title, icon, add_callback):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6, hexpand=True)
        lbl = Gtk.Label(label=f"<b>{title}</b>", use_markup=True, xalign=0)
        box.append(lbl)

        scroll = Gtk.ScrolledWindow(vexpand=True)
        lst = Gtk.ListBox()
        lst.set_selection_mode(Gtk.SelectionMode.NONE)
        lst.add_css_class("boxed-list")
        scroll.set_child(lst)
        box.append(scroll)

        btn = Gtk.Button(label="Add Entry", icon_name=icon)
        btn.props.hexpand = False
        btn.props.halign = Gtk.Align.START
        btn.connect("clicked", add_callback)
        box.append(btn)
        
        box._list = lst
        return box

    def add_row_to_list(self, listbox, key="", value="", is_custom=False, schema=None):
        row_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        
        # --- PART 1: THE KEY (LHS) ---
        if not is_custom:
            # Stream Options (Global) use the original Picker
            ent_key = Gtk.Button(label=key if key else "Select...")
            ent_key.connect("clicked", lambda b: self.on_probe_picker_clicked(b, listbox))
            self.global_keys_group.add_widget(ent_key)
        else:
            # Encoder Options use the new EncoderParameterPickerWindow
            ent_key = Gtk.Button(label=key if key else "Select...")
            ent_key.connect("clicked", lambda b: self.on_encoder_picker_clicked(b, listbox))
            self.private_keys_group.add_widget(ent_key)

        # --- PART 2: THE VALUE (RHS) ---
        value_widget = None
        
        # If we are loading an existing template, try to find the schema in our YAML
        if not schema and is_custom and key:
            try:
                with open("./codecs/parameters.yaml", "r") as f:
                    full_params = yaml.safe_load(f)
                schema = full_params.get(self.selected_codec, {}).get("parameters", {}).get(key)
            except: pass

        if schema:
            p_type = schema.get("type", "string")
            options = schema.get("options")

            if p_type == "enum" and options:
                # Build list of strings for DropDown
                choices = []
                # Handle the mixed Dictionary or List logic
                if isinstance(options, dict):
                    row_box._tech_values = [str(k) for k in options.keys()]
                    choices = [f"{v['sdesc']} ({v['ldesc']})" for v in options.values()]
                else:
                    row_box._tech_values = [str(o) for o in options]
                    choices = [str(o) for o in options]
                
                # Create a custom factory to control the label properties
                factory = Gtk.SignalListItemFactory()
                
                def setup_factory(factory, list_item):
                    # This creates the label used in the dropdown rows AND the button
                    label = Gtk.Label(xalign=0)
                    label.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
                    list_item.set_child(label)

                def bind_factory(factory, list_item):
                    # This binds the text from the string list to the label
                    label = list_item.get_child()
                    string_obj = list_item.get_item()
                    label.set_label(string_obj.get_string())

                factory.connect("setup", setup_factory)
                factory.connect("bind", bind_factory)

                # Create the dropdown with the custom factory
                model = Gtk.StringList.new(choices)
                value_widget = Gtk.DropDown(model=model, factory=factory, list_factory=factory)
                
                # Crucial for ellipsizing: allow the widget to shrink
                value_widget.set_hexpand(True)
                value_widget.set_halign(Gtk.Align.FILL)

                # This prevents the label from requesting its full natural width
                value_widget.set_size_request(100, -1)
                
                # Set initial selection if value exists
                if value and hasattr(row_box, "_tech_values"):
                    try:
                        idx = row_box._tech_values.index(str(value))
                        value_widget.set_selected(idx)
                    except ValueError: pass

            elif p_type in ["integer", "float"]:
                is_int = (p_type == "integer")
                adj = Gtk.Adjustment(
                    value=float(value) if value else float(schema.get("default", 0)),
                    lower=float(schema.get("min", -999999)),
                    upper=float(schema.get("max", 999999)),
                    step_increment=1.0 if is_int else 0.1,
                    page_increment=10.0,
                    page_size=0
                )
                value_widget = Gtk.SpinButton(adjustment=adj, numeric=True)
                if not is_int:
                    value_widget.set_digits(2)
            
            elif p_type == "boolean":
                value_widget = Gtk.Switch()
                value_widget.set_active(str(value).lower() in ['true', '1', 'on'])
                value_widget.set_halign(Gtk.Align.START)

        # Fallback to standard Entry if no schema matches or type is string
        if not value_widget:
            value_widget = Gtk.Entry(text=str(value), placeholder_text="value", hexpand=True)

        value_widget.set_hexpand(True)
        btn_del = Gtk.Button(icon_name="user-trash-symbolic")
        
        row_box.append(ent_key)
        row_box.append(value_widget)
        row_box.append(btn_del)
        
        row = Gtk.ListBoxRow(child=row_box)
        row._key_widget = ent_key
        row._val_widget = value_widget
        btn_del.connect("clicked", lambda *_: self.remove_row(listbox, row, is_custom))
        listbox.append(row)

    def on_encoder_picker_clicked(self, button, listbox):
        """New handler for Encoder Options that utilizes the YAML schema"""
        from UI.EncoderParameterPickerWindow import EncoderParameterPickerWindow
        
        def on_selected(key, schema):
            # Refresh the row with the proper widget type
            parent_row = button.get_ancestor(Gtk.ListBoxRow)
            listbox.remove(parent_row)
            self.add_row_to_list(listbox, key=key, is_custom=True, schema=schema)

        picker = EncoderParameterPickerWindow(self, self.selected_codec, on_selected)
        picker.present()

    def remove_row(self, listbox, row, is_custom):
        # Remove from SizeGroup before removing from listbox
        if is_custom:
            self.private_keys_group.remove_widget(row._key_widget)
        else:
            self.global_keys_group.remove_widget(row._key_widget)
            
        listbox.remove(row)

    def on_add_global(self, _):
        self.add_row_to_list(self.lst_global, is_custom=False)

    def on_add_private(self, _):
        self.add_row_to_list(self.lst_private, is_custom=True)

    def on_probe_picker_clicked(self, button, listbox):
        # We define a callback for when the picker selects a parameter
        def on_param_selected(p):
            # Change the button label to the parameter name
            button.set_label(p['name'])
            # (Optional) If you want to auto-set a default value, do it here
            
        # This opens your existing ParameterPickerWindow (for PyAV probe options)
        picker = ParameterPickerWindow(self, self.selected_codec, on_param_selected)
        picker.present()

    def load_structured_template(self, template):
        data = template.get('data', {})
        self.entry_name.props.text = template['name']
        if template['name']:
            self.entry_name.props.can_focus = False
            self.entry_name.props.editable = False
        self.selected_codec = data['codec']
        params = data.get('parameters', {})

        # Set the DropDown index based on the type string
        if self.locked_type:
            try:
                # Force the index to match the locked type
                type_idx = all_types.index(self.locked_type.lower())
                self.combo_type.set_selected(type_idx)
                # Lock the UI
                self.combo_type.set_sensitive(False) 
                self.combo_type.set_tooltip_text(f"Type is locked to {self.locked_type} for this context.")
            except ValueError:
                pass
        else:
            try:
                type_idx = all_types.index(data.get('type', 'video').lower())
                self.combo_type.set_selected(type_idx)
            except ValueError:
                pass
        
        # Load Globals (parameters:)
        for k, v in params.items():
            if k != 'options':
                self.add_row_to_list(self.lst_global, k, v, is_custom=False)
        
        # Load Privates (parameters: options:)
        options = params.get('options', {})
        for k, v in options.items():
            self.add_row_to_list(self.lst_private, k, v, is_custom=True)

    def get_template_yaml_data(self):
        output = {
            "type": self.get_selected_type(),
            "codec": self.selected_codec,
            "parameters": {"options": {}}
        }

        def extract_value(row):
            widget = row._val_widget
            box = row.get_child()
            
            if isinstance(widget, Gtk.DropDown):
                idx = widget.get_selected()
                # Return the technical value (0, 1, or 'slow') rather than the UI label
                return box._tech_values[idx] if hasattr(box, "_tech_values") else ""
            elif isinstance(widget, Gtk.SpinButton):
                return widget.get_value() if widget.get_digits() > 0 else int(widget.get_value())
            elif isinstance(widget, Gtk.Switch):
                return widget.get_active()
            elif isinstance(widget, Gtk.Entry):
                return widget.get_text()
            return ""

        # Collect Globals
        row = self.lst_global.get_first_child()
        while row:
            key = row._key_widget.get_label() if isinstance(row._key_widget, Gtk.Button) else row._key_widget.get_text()
            if key != "Select...":
                output["parameters"][key] = extract_value(row)
            row = row.get_next_sibling()

        # Collect Privates (Encoder Options)
        row = self.lst_private.get_first_child()
        while row:
            key = row._key_widget.get_label() if isinstance(row._key_widget, Gtk.Button) else row._key_widget.get_text()
            if key != "Select...":
                output["parameters"]["options"][key] = extract_value(row)
            row = row.get_next_sibling()

        return output

    def update_codec_ui(self):
        """Refreshes the 'pill' display for the codec"""
        while child := self.codec_box.get_first_child():
            self.codec_box.remove(child)
        
        # Create the pill (similar to DispositionTag but specific for the one choice)
        tag = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        tag.add_css_class("codec-tag") 
        
        lbl = Gtk.Label(label=self.selected_codec)
        lbl.set_margin_start(8)
        lbl.set_margin_end(8)
        tag.append(lbl)
        
        btn_edit = Gtk.Button(icon_name="search-symbolic", tooltip_text="Search For Codec")
        btn_edit.set_has_frame(False)
        btn_edit.connect("clicked", self.on_change_codec_clicked)
        tag.append(btn_edit)
        
        self.codec_box.append(tag)

    def on_type_changed(self, dropdown, pspec):
        """Triggered when user changes Video/Audio/Subtitle etc."""
        new_type = self.get_selected_type()
        self.template['data']['type'] = new_type
        print(f"Template type updated to: {new_type}")

    def on_codec_selected(self, codec):
        """Triggered when user picks a codec from the search window"""
        self.selected_codec = codec
        self.template['data']['codec'] = codec # Keep the dictionary in sync
        self.update_codec_ui()

    def on_change_codec_clicked(self, button):
        # Pass the CURRENT type from the template data to the picker
        current_type = self.locked_type if self.locked_type else self.get_selected_type()
        wnd = CodecPickerWindow(
            parent_window=self, 
            codec_type=current_type, 
            on_select=self.on_codec_selected
        )
        wnd.present()

    def get_selected_type(self):
        idx = self.combo_type.get_selected()
        return all_types[idx]
    
    def on_save_clicked(self, button):
        # 1. Collect the data from the UI
        template_name = self.entry_name.get_text().strip()
        
        if not template_name:
            # Simple validation to ensure we have a filename
            self.show_error_dialog("Template name cannot be empty.")
            return

        # 2. Get the structured data (the method we built earlier)
        yaml_data = self.get_template_yaml_data()

        # --- CUSTOM SERIALIZATION LOGIC ---
        
        class LiteralDumper(yaml.SafeDumper):
            """Custom dumper to force quotes on strings and handle formatting"""
            pass

        # def string_representer(dumper, data):
        #     # Force single quotes for all strings to ensure 'constrained' 
        #     # is handled as a literal string
        #     return dumper.represent_scalar('tag:yaml.org,2002:str', data, style="'")
        
        # LiteralDumper.add_representer(str, string_representer)
        
        # 3. Determine the save path
        # If we are editing (template exists), use its path. 
        # Otherwise, use the ./templates/ directory in the current working dir.
        if self.template['path']:
            save_path = Path(self.template['path'])
        else:
            base_dir = Path("./templates")
            base_dir.mkdir(exist_ok=True) # Ensure directory exists
            save_path = base_dir / f"{template_name}.yaml"

        try:
            # 4. Write to disk
            with open(save_path, 'w') as f:
                # We save only the 'data' part to the YAML file to match your structure
                yaml.dump(yaml_data, f, sort_keys=False, indent=4)
            
            print(f"Successfully saved template to {save_path}")
            
            if self.on_save_callback:
                self.on_save_callback(template_name)
                
            self.destroy()
            
        except Exception as e:
            self.show_error_dialog(f"Failed to save template: {str(e)}")

    def show_error_dialog(self, message):
        # Quick helper for feedback
        dialog = Gtk.MessageDialog(
            transient_for=self,
            modal=True,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text=message
        )
        dialog.connect("response", lambda d, r: d.destroy())
        dialog.show()