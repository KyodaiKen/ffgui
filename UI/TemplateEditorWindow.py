import gi
gi.require_version("Gdk", "4.0")
from gi.repository import Gtk, Gdk, Pango
from UI.CodecPickerWindow import CodecPickerWindow
from UI.EncoderParameterPickerWindow import EncoderParameterPickerWindow
from UI.Core import UICore
import copy
import yaml
from pathlib import Path

class TemplateEditorWindow(Gtk.ApplicationWindow):
    def __init__(self, parent_window, template, on_save_callback=None, locked_type=None, **kwargs):
        super().__init__(**kwargs, title="Template Editor")

        # 1. State Initialization
        self.app = Gtk.Application.get_default()
        self.on_save_callback = on_save_callback
        self.locked_type = locked_type
        self.all_types = UICore.get_all_types()
        self.encoder_keys_group = Gtk.SizeGroup(mode=Gtk.SizeGroupMode.HORIZONTAL)

        # 2. Template Setup
        self.template = self._prepare_template_data(template)
        self.selected_codec = self.template['data']['codec']

        # 3. Window Configuration
        self.set_default_size(1024, 700)
        self.set_transient_for(parent_window)
        self.set_modal(True)

        # 4. Build UI
        self._setup_css()
        self._build_ui()

        # 5. Fill Data
        self.load_structured_template(self.template)
        self.update_codec_ui()

    def _prepare_template_data(self, template):
        if template:
            return copy.deepcopy(template)
        return {
            "name": "", "path": "", "origin": "System",
            "data": {
                "type": "video", "codec": "libx264",
                "parameters": {"options": {}}
            }
        }

    def _setup_css(self):
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data("""
            .codec-tag { background-color: alpha(@theme_fg_color, 0.05); border: 1px solid mix(@theme_fg_color, @theme_bg_color, 0.8); border-radius: 6px; padding: 2px; }
            .codec-tag label { margin-start: 8px; margin-end: 8px; font-weight: bold; }
            dropdown > button > box > stack > row.activatable { background-color: transparent; }
            #template-editor-column popover box { min-width: 180px; }
        """, -1)
        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), css_provider, Gtk.STYLE_PROVIDER_PRIORITY_USER)

    def _build_ui(self):
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        # Using discrete margins
        main_box.set_margin_start(12)
        main_box.set_margin_end(12)
        main_box.set_margin_top(12)
        main_box.set_margin_bottom(12)
        self.set_child(main_box)

        # Header Grid (Name, Type, Codec)
        grid = Gtk.Grid(row_spacing=10, column_spacing=10)
        main_box.append(grid)

        self.entry_name = Gtk.Entry(hexpand=True, placeholder_text="Template Name...")
        self.combo_type = Gtk.DropDown.new_from_strings([t.capitalize() for t in self.all_types])
        self.combo_type.props.halign = Gtk.Align.START
        self.combo_type.connect("notify::selected", self.on_type_changed)
        self.codec_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)

        grid.attach(Gtk.Label(label="Name:", halign=Gtk.Align.END), 0, 0, 1, 1)
        grid.attach(self.entry_name, 1, 0, 1, 1)
        grid.attach(Gtk.Label(label="Type:", halign=Gtk.Align.END), 0, 1, 1, 1)
        grid.attach(self.combo_type, 1, 1, 1, 1)
        grid.attach(Gtk.Label(label="Codec:", halign=Gtk.Align.END), 0, 2, 1, 1)
        grid.attach(self.codec_box, 1, 2, 1, 1)

        main_box.append(Gtk.Separator())

        # Main Columns
        list_container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=18, vexpand=True)
        list_container.set_homogeneous(True)
        main_box.append(list_container)

        self.lst_encoder = self._create_column(list_container, "Encoder Options", self.on_add_encoder_param)
        self.lst_filters = self._create_column(list_container, "Filters", self.on_add_filter, is_filter=True)

        # Footer Actions
        btn_save = Gtk.Button(label="Save Template")
        btn_save.add_css_class("suggested-action")
        btn_save.set_halign(Gtk.Align.END)
        btn_save.connect("clicked", self.on_save_clicked)
        main_box.append(btn_save)

    def _create_column(self, container, title, add_callback, is_filter=False):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6, hexpand=True)

        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        header.append(Gtk.Label(label=f"<b>{title}</b>", use_markup=True, xalign=0, hexpand=True))

        btn_add = Gtk.Button(icon_name="list-add-symbolic")
        btn_add.add_css_class("flat")
        btn_add.connect("clicked", add_callback)
        header.append(btn_add)
        box.append(header)

        if is_filter:
            mode_hbox = Gtk.Box(spacing=6)
            mode_hbox.append(Gtk.Label(label="Mode:"))
            self.combo_filter_mode = Gtk.DropDown.new_from_strings(["Simple", "Complex"])
            mode_hbox.append(self.combo_filter_mode)
            box.append(mode_hbox)

        # Corrected ScrolledWindow and ListBox initialization
        scroll = Gtk.ScrolledWindow(vexpand=True)
        lst = Gtk.ListBox()
        lst.add_css_class("boxed-list")
        lst.set_name("template-editor-column")
        lst.set_selection_mode(Gtk.SelectionMode.NONE)

        scroll.set_child(lst)
        box.append(scroll)
        container.append(box)
        return lst

    # --- WIDGET FACTORY ---

    def _parse_ffmpeg_num(self, val, fallback=0):
        """Extracts the first numeric part of a string like '51, 0 means auto'."""
        if isinstance(val, (int, float)):
            return float(val)
        if not val:
            return float(fallback)
        try:
            # Take the first word and strip non-numeric characters
            clean = str(val).split(',')[0].split(' ')[0]
            return float(''.join(c for c in clean if c.isdigit() or c in '.-'))
        except (ValueError, IndexError):
            return float(fallback)

    def create_value_widget(self, key, value, schema=None):
        if not schema and key:
            pool = self.get_codec_params_list()
            schema = next((p for p in pool if p.get('name') == key), None)

        if not schema:
            return Gtk.Entry(text=str(value if value is not None else ""), hexpand=True)

        # 1. PRIORITY: If there are options, it's a DropDown, regardless of 'type'
        options_list = schema.get("options", [])
        if options_list:
            tech_values = [str(o.get('name')) for o in options_list]
            display_names = [f"{o.get('name')} ({o.get('descr')})" if o.get('descr') else str(o.get('name')) for o in options_list]
            
            w = Gtk.DropDown(model=Gtk.StringList.new(display_names), hexpand=True)
            w._tech_values = tech_values
            
            # Determine initial selection
            cur_val = str(value) if value is not None else str(schema.get("default", ""))
            try:
                if cur_val in tech_values:
                    w.set_selected(tech_values.index(cur_val))
            except ValueError:
                pass
            return w

        # 2. NUMERIC: Logic for Spinners
        p_type = str(schema.get("type", "string")).lower()
        if any(t in p_type for t in ["int", "integer", "float", "double"]):
            # Check if this is a floating point value
            is_float = any(x in p_type for x in ["float", "double"])
            
            v_min = self._parse_ffmpeg_num(schema.get("min"), -2147483648)
            v_max = self._parse_ffmpeg_num(schema.get("max"), 2147483647)
            
            # Value handling
            if value is None or value == "":
                v_cur = self._parse_ffmpeg_num(schema.get("default"), 0)
            else:
                v_cur = self._parse_ffmpeg_num(value, 0)

            # Use 0.1 steps for floats, 1.0 for integers
            # step = 0.1 if is_float else 1.0
            step = 1
            adj = Gtk.Adjustment(value=v_cur, lower=v_min, upper=v_max,
                                 step_increment=step, page_increment=step * 10)
            
            w = Gtk.SpinButton(adjustment=adj, numeric=True)
            
            if is_float:
                # CRITICAL: This allows the 22.1 to actually be displayed
                w.set_digits(1) 
            else:
                w.set_digits(0)

            w.set_value(v_cur) 
            return w

        # 3. BOOLEAN
        if p_type in ["bool", "boolean"]:
            active = str(value).lower() in ['true', '1', 'on'] if value is not None else bool(schema.get("default"))
            return Gtk.Switch(active=active, halign=Gtk.Align.START)

        return Gtk.Entry(text=str(value if value is not None else ""), hexpand=True)

    # --- ROW MANAGEMENT ---

    def add_row_to_list(self, listbox, key="", value="", schema=None):
        row_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        # 1. The Key Button
        btn_key = Gtk.Button(label=key or "Select...", width_request=150)
        self.encoder_keys_group.add_widget(btn_key)

        if listbox == self.lst_encoder:
            btn_key.connect("clicked", self.on_encoder_picker_clicked)

        # 2. The Value Widget
        val_widget = self.create_value_widget(key, value, schema)

        # 3. THE FIX: Add a spacer to push the delete button to the right
        # This widget will gobble up all empty space between the switch and trash icon
        spacer = Gtk.Box(hexpand=True)

        # 4. The Delete Button
        btn_del = Gtk.Button(icon_name="user-trash-symbolic")

        row_box.append(btn_key)
        row_box.append(val_widget)
        row_box.append(spacer) # Inserted spacer
        row_box.append(btn_del)

        row = Gtk.ListBoxRow(child=row_box)
        row._key_widget, row._val_widget = btn_key, val_widget

        btn_del.connect("clicked", lambda *_: listbox.remove(row))
        listbox.append(row)

    # --- DATA FLOW ---

    def get_codec_params_list(self):
        data = getattr(self.app, 'ffmpeg_data', {})
        if not data:
            return []

        all_params = []
        stream_type = self.get_selected_type() # "video", "audio", etc.

        # 1. Get Codec-Specific Params
        codecs = data.get('codecs', [])
        codec_obj = next((c for c in codecs if c.get('name') == self.selected_codec), None)
        if codec_obj:
            all_params.extend(codec_obj.get("parameters", []))

        # 2. Get Global Params (Matching your Picker logic)
        groups = data.get('globals', [])
        for group in groups:
            group_name = group.get("name", "").lower()

            # Filter logic matching your EncoderParameterPickerWindow
            should_include = (group_name == "av_options") or \
                             (group_name == "video" and stream_type == "video") or \
                             (group_name == "audio" and stream_type == "audio") or \
                             (group_name == "subtitle" and stream_type == "subtitle")

            if should_include:
                # Add these global parameters to our search pool
                all_params.extend(group.get("parameters", []))

        return all_params

    # --- HANDLERS ---

    def on_add_encoder_param(self, _):
        def on_selected(k):
            self.add_row_to_list(self.lst_encoder, k, value=None)

        picker = EncoderParameterPickerWindow(
            self,
            self.selected_codec,
            self.get_selected_type(),
            self.get_codec_params_list(),
            on_selected
        )
        picker.present()

    def on_encoder_picker_clicked(self, button):
        row = button.get_parent().get_parent()
        def on_selected(k):
            button.set_label(k)
            row_box = row.get_child()
            row_box.remove(row._val_widget)

            # We call create_value_widget with no schema; it will look it up itself
            new_w = self.create_value_widget(k, value=None, schema=None)

            row_box.insert_child_after(new_w, button)
            row._val_widget = new_w

        picker = EncoderParameterPickerWindow(
            self,
            self.selected_codec,
            self.get_selected_type(),
            self.get_codec_params_list(),
            on_selected
        )
        picker.present()

    def update_codec_ui(self):
        while child := self.codec_box.get_first_child(): self.codec_box.remove(child)
        tag = Gtk.Box(css_classes=["codec-tag"])
        tag.append(Gtk.Label(label=self.selected_codec, margin_start=6, margin_end=6, margin_top=6, margin_bottom=6))
        btn = Gtk.Button(icon_name="search-symbolic", has_frame=False)
        btn.connect("clicked", self.on_change_codec_clicked)
        tag.append(btn)
        self.codec_box.append(tag)

    def on_change_codec_clicked(self, _):
        CodecPickerWindow(parent_window=self, codec_type=self.get_selected_type(), on_select=lambda c: (setattr(self, 'selected_codec', c), self.update_codec_ui())).present()

    def on_type_changed(self, *args):
        self.template['data']['type'] = self.get_selected_type()

    def get_selected_type(self):
        return self.all_types[self.combo_type.get_selected()]

    def load_structured_template(self, template):
        # The YAML structure has 'name' at top level and 'codec'/'type' inside 'data' or top level
        name = template.get('name', '')
        self.entry_name.set_text(name)

        # Lock name if we are editing an existing system template or named file
        if name:
            self.entry_name.set_editable(False)
            self.entry_name.set_can_focus(False)

        # Normalize data access
        data = template.get('data', template)
        self.selected_codec = data.get('codec', 'libx264')

        # Update Type Dropdown
        target_type = self.locked_type or data.get('type', 'video')
        try:
            idx = self.all_types.index(target_type.lower())
            self.combo_type.set_selected(idx)
        except (ValueError, AttributeError):
            pass

        # Add rows - create_value_widget will handle its own schema lookup now
        params = data.get('parameters', {}).get('options', {})
        for k, v in params.items():
            self.add_row_to_list(self.lst_encoder, k, v)

    def show_error_dialog(self, message):
        """Standard GTK4 Message Dialog helper."""
        dialog = Gtk.AlertDialog(message=message)
        dialog.show(self)

    def on_save_clicked(self, _):
        # 1. Get the name from the Entry widget
        name = self.entry_name.get_text().strip()

        # 2. Validation
        if not name:
            self.show_error_dialog("Template name cannot be empty.")
            return

        # 3. Reconstruct the template data from the UI rows
        options = {}
        row = self.lst_encoder.get_first_child()
        while row:
            # list_box rows in GTK4 can be separators or headers, so check for our attributes
            if hasattr(row, "_key_widget") and hasattr(row, "_val_widget"):
                key = row._key_widget.get_label()
                if key != "Select...":
                    options[key] = self.extract_widget_value(row._val_widget)
            row = row.get_next_sibling()

        # 4. Build the YAML structure
        # Note: We include 'name' at the top level of the file so it can be loaded back
        yaml_data = {
            "name": name,
            "type": self.get_selected_type(),
            "codec": self.selected_codec,
            "parameters": {"options": options},
            "filters": {
                "mode": self.combo_filter_mode.get_selected_item().get_string().lower() if hasattr(self, 'combo_filter_mode') else "simple",
                "entries": []
            }
        }

        # 5. Determine Save Path
        # If we have an existing path, keep it. Otherwise, create a new one.
        if self.template.get('path'):
            save_path = Path(self.template['path'])
        else:
            base_dir = Path("./templates")
            base_dir.mkdir(exist_ok=True)
            save_path = base_dir / f"{name.replace(' ', '_')}.yaml"

        # 6. Save
        try:
            with open(save_path, 'w') as f:
                yaml.dump(yaml_data, f, sort_keys=False, indent=4)

            if self.on_save_callback:
                self.on_save_callback(name)

            self.destroy()

        except Exception as e:
            self.show_error_dialog(f"Failed to save template: {str(e)}")

    def extract_widget_value(self, w):
        """Helper to get the technical value from various widget types."""
        if isinstance(w, Gtk.DropDown):
            # Use our custom attribute stored during creation
            if hasattr(w, "_tech_values"):
                return w._tech_values[w.get_selected()]
            return w.get_selected_item().get_string()

        elif isinstance(w, Gtk.SpinButton):
            # Check if it's effectively an integer
            val = w.get_value()
            return int(val) if val.is_integer() else val

        elif isinstance(w, Gtk.Switch):
            return w.get_active()

        elif isinstance(w, Gtk.Entry):
            return w.get_text()

        elif isinstance(w, Gtk.MenuButton) and hasattr(w, "_check_buttons"):
            # Flag extraction
            active = [k for k, (cb, _) in w._check_buttons.items() if cb.get_active()]
            return "+".join(active)

        return ""

    def on_add_filter(self, _): pass
