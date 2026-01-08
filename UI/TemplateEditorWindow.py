import gi
gi.require_version("Gdk", "4.0")
from gi.repository import Gtk, Gdk, Pango
from UI.CodecPickerWindow import CodecPickerWindow
from UI.EncoderParameterPickerWindow import EncoderParameterPickerWindow
from UI.Core import UICore
import copy
import yaml
from pathlib import Path

all_types = UICore.get_all_types()

class TemplateEditorWindow(Gtk.ApplicationWindow):
    def __init__(self, parent_window, template, on_save_callback=None, locked_type=None, **kwargs):
        super().__init__(**kwargs, title="Template Editor")
        self.on_save_callback = on_save_callback
        self.locked_type = locked_type
        self.selected_codec = ""

        self.encoder_keys_group = Gtk.SizeGroup(mode=Gtk.SizeGroupMode.HORIZONTAL)
        self.schemas = {}

        # Safely get the application instance
        self.app = self.get_application()
        if not self.app:
            self.app = Gtk.Application.get_default()

        if not self.app or not hasattr(self.app, 'ffmpeg_data'):
            print("Warning: ffmpeg_data not found in App instance")

        # Set window size
        self.set_size_request(640, 480)
        self.set_default_size(1024, 700)
        self.set_transient_for(parent_window)
        self.set_modal(True)

        self._setup_css()
        self._build_ui()

        # Load existing data or defaults
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

        self.selected_codec = self.template['data']['codec']

        if template:
            self.load_structured_template(self.template)

        self.update_codec_ui()

    def _setup_css(self):
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
            dropdown > button > box > stack > row.activatable:hover,
            dropdown > button > box > stack > row.activatable:selected,
            dropdown > button > box > stack > row.activatable {
                background-color: transparent;
                background-image: none;
                box-shadow: none;
                outline: none;
            }
            menubutton.text-button {
                padding-left: 8px;
                padding-right: 8px;
            }
            popover box {
                min-width: 150px;
            }
        """, -1)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_USER
        )

    def _build_ui(self):
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        main_box.set_margin_start(6)
        main_box.set_margin_end(6)
        main_box.set_margin_top(6)
        main_box.set_margin_bottom(6)
        self.set_child(main_box)

        grid = Gtk.Grid(row_spacing=10, column_spacing=10)
        main_box.append(grid)

        grid.attach(Gtk.Label(label="Name:", halign=Gtk.Align.END), 0, 0, 1, 1)
        self.entry_name = Gtk.Entry(hexpand=True)
        grid.attach(self.entry_name, 1, 0, 1, 1)

        grid.attach(Gtk.Label(label="Type:", halign=Gtk.Align.END), 0, 1, 1, 1)
        self.combo_type = Gtk.DropDown.new_from_strings([t.capitalize() for t in all_types])
        self.combo_type.set_halign(Gtk.Align.START)
        self.combo_type.set_size_request(108, -1)
        self.combo_type.connect("notify::selected", self.on_type_changed)
        grid.attach(self.combo_type, 1, 1, 1, 1)

        grid.attach(Gtk.Label(label="Codec:", halign=Gtk.Align.END), 0, 2, 1, 1)
        self.codec_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        grid.attach(self.codec_box, 1, 2, 1, 1)

        main_box.append(Gtk.Separator())

        list_container = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=18, vexpand=True)
        main_box.append(list_container)

        col_left = self.create_list_column("Encoder Options", "list-add-symbolic", self.on_add_encoder_param)
        self.lst_encoder = col_left._list
        list_container.append(col_left)

        col_right = self.create_filter_column()
        self.lst_filters = col_right._list
        list_container.append(col_right)

        btn_save = Gtk.Button(label="Save Template")
        btn_save.add_css_class("suggested-action")
        btn_save.set_halign(Gtk.Align.END)
        btn_save.connect("clicked", self.on_save_clicked)
        main_box.append(btn_save)

    def _load_yaml(self, path):
        try:
            with open(path, "r") as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"Error loading {path}: {e}")
            return {}

    def create_list_column(self, title, icon, add_callback):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6, hexpand=True)
        header_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        lbl = Gtk.Label(label=f"<b>{title}</b>", use_markup=True, xalign=0, hexpand=True)
        btn_add = Gtk.Button(icon_name=icon)
        btn_add.add_css_class("flat")
        btn_add.connect("clicked", add_callback)
        header_hbox.append(lbl)
        header_hbox.append(btn_add)
        box.append(header_hbox)

        scroll = Gtk.ScrolledWindow(vexpand=True)
        lst = Gtk.ListBox()
        lst.set_selection_mode(Gtk.SelectionMode.NONE)
        lst.add_css_class("boxed-list")
        scroll.set_child(lst)
        box.append(scroll)
        box._list = lst
        return box

    def create_filter_column(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6, hexpand=True)
        header_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        lbl = Gtk.Label(label="<b>Filters</b>", use_markup=True, xalign=0, hexpand=True)
        btn_add = Gtk.Button(icon_name="list-add-symbolic")
        btn_add.add_css_class("flat")
        btn_add.connect("clicked", self.on_add_filter)
        header_hbox.append(lbl)
        header_hbox.append(btn_add)
        box.append(header_hbox)

        mode_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        mode_hbox.append(Gtk.Label(label="Filter Type:", xalign=0))
        self.combo_filter_mode = Gtk.DropDown.new_from_strings(["Simple", "Complex"])
        self.combo_filter_mode.set_hexpand(True)
        mode_hbox.append(self.combo_filter_mode)
        box.append(mode_hbox)

        scroll = Gtk.ScrolledWindow(vexpand=True)
        lst = Gtk.ListBox()
        lst.set_selection_mode(Gtk.SelectionMode.NONE)
        lst.add_css_class("boxed-list")
        scroll.set_child(lst)
        box.append(scroll)
        box._list = lst
        return box

    # --- ROW MANAGEMENT ---

    def create_value_widget(self, key, value, schema):
        """Standardized factory to create the RHS widget based on schema."""
        value_widget = None

        # Fix the fallback to use the dynamic app data instead of self.schemas
        if not schema and key:
            params = self.get_codec_params_list()
            schema = next((p for p in params if p.get('name') == key), None)

        if schema:
            p_type = schema.get("type", "string")
            options = schema.get("options")

            if p_type == "enum" and options:
                choices = []
                tech_values = []
                if isinstance(options, dict):
                    tech_values = [str(k) for k in options.keys()]
                    choices = [f"{v.get('sdesc', k)} ({v.get('ldesc', '')})" for k, v in options.items()]
                else:
                    tech_values = [str(o) for o in options]
                    choices = [str(o) for o in options]

                model = Gtk.StringList.new(choices)
                value_widget = Gtk.DropDown(model=model)
                value_widget._tech_values = tech_values
                value_widget.set_hexpand(True)

                if value:
                    try:
                        idx = tech_values.index(str(value))
                        value_widget.set_selected(idx)
                    except ValueError: pass

            elif p_type in ["integer", "float"]:
                is_int = (p_type == "integer")
                adj = Gtk.Adjustment(
                    value=float(value) if value else float(schema.get("default", 0)),
                    lower=float(schema.get("min", -999999)),
                    upper=float(schema.get("max", 999999)),
                    step_increment=1.0 if is_int else 0.1
                )
                value_widget = Gtk.SpinButton(adjustment=adj, numeric=True)
                if not is_int: value_widget.set_digits(2)

            elif p_type == "flags" and options:
                value_widget = Gtk.MenuButton(label="None Selected", hexpand=True)
                popover = Gtk.Popover()
                vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
                vbox.set_margin_start(6)
                vbox.set_margin_end(6)
                vbox.set_margin_top(6)
                vbox.set_margin_bottom(6)

                selected_flags = str(value).split("+") if value else []
                check_buttons = {}

                def update_flag_label(*_):
                    active = [info['sdesc'] for k, (cb, info) in check_buttons.items() if cb.get_active()]
                    value_widget.set_label("+".join(active) if active else "None")

                for f_key, f_info in options.items():
                    cb = Gtk.CheckButton(label=f_info.get('sdesc', f_key))
                    cb.set_active(f_key in selected_flags)
                    cb.connect("toggled", update_flag_label)
                    vbox.append(cb)
                    check_buttons[f_key] = (cb, f_info)

                popover.set_child(vbox)
                value_widget.set_popover(popover)
                value_widget._check_buttons = check_buttons
                update_flag_label()

            elif p_type == "boolean":
                value_widget = Gtk.Switch()
                value_widget.set_active(str(value).lower() in ['true', '1', 'on'])
                value_widget.set_halign(Gtk.Align.START)

        if not value_widget:
            value_widget = Gtk.Entry(text=str(value), hexpand=True)

        return value_widget

    def add_row_to_list(self, listbox, key="", value="", schema=None):
        row_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        btn_key = Gtk.Button(label=key if key else "Select...")
        btn_key.set_size_request(150, -1)

        # This will now find the attribute successfully
        self.encoder_keys_group.add_widget(btn_key)

        if listbox == self.lst_encoder:
            btn_key.connect("clicked", lambda b: self.on_encoder_picker_clicked(b, listbox))

        value_widget = self.create_value_widget(key, value, schema)
        value_widget.set_hexpand(True)
        value_widget.set_halign(Gtk.Align.FILL)

        btn_del = Gtk.Button(icon_name="user-trash-symbolic")

        row_box.append(btn_key)
        row_box.append(value_widget)
        row_box.append(btn_del)

        row = Gtk.ListBoxRow(child=row_box)
        row._key_widget = btn_key
        row._val_widget = value_widget

        btn_del.connect("clicked", lambda *_: listbox.remove(row))
        listbox.append(row)

    def refresh_row_value_widget(self, row, key, schema):
        """Swaps the value widget in an existing row."""
        row_box = row.get_child()
        key_button = row._key_widget
        old_value_widget = row._val_widget

        row_box.remove(old_value_widget)
        new_value_widget = self.create_value_widget(key, "", schema)

        row_box.insert_child_after(new_value_widget, key_button)
        row._val_widget = new_value_widget

    # --- CALLBACKS & LOGIC ---

    def get_codec_params_list(self):
        # Search the list of codecs for the one currently selected in the UI
        all_codecs = self.app.ffmpeg_data.get('codecs', [])
        codec_obj = next((c for c in all_codecs if c['name'] == self.selected_codec), None)

        # Return the actual parameters list (where 'preset' lives)
        return codec_obj.get("parameters", []) if codec_obj else []

    def on_add_encoder_param(self, _):
        def on_selected(key, schema):
            self.add_row_to_list(self.lst_encoder, key=key, schema=schema)

        current_type = self.get_selected_type()

        # Use the helper that now has the Gtk.Application.get_default() fallback
        codec_schema = self.get_codec_params_list()

        picker = EncoderParameterPickerWindow(
            self, self.selected_codec, current_type, codec_schema, on_selected
        )
        picker.present()

    def on_encoder_picker_clicked(self, button, listbox):
        row = button.get_parent().get_parent()

        def on_selected(new_key, new_schema):
            button.set_label(new_key)
            self.refresh_row_value_widget(row, new_key, new_schema)

        current_type = self.get_selected_type()

        # Use the same helper here
        codec_schema = self.get_codec_params_list()

        picker = EncoderParameterPickerWindow(
            self, self.selected_codec, current_type, codec_schema, on_selected
        )
        picker.present()

    def on_add_filter(self, _):
        # Placeholder
        pass

    def on_type_changed(self, dropdown, pspec):
        new_type = self.get_selected_type()
        self.template['data']['type'] = new_type

    def on_codec_selected(self, codec):
        self.selected_codec = codec
        self.template['data']['codec'] = codec
        self.update_codec_ui()

    def on_change_codec_clicked(self, button):
        current_type = self.locked_type if self.locked_type else self.get_selected_type()
        wnd = CodecPickerWindow(
            parent_window=self,
            codec_type=current_type,
            on_select=self.on_codec_selected
        )
        wnd.present()

    def update_codec_ui(self):
        while child := self.codec_box.get_first_child():
            self.codec_box.remove(child)

        tag = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        tag.add_css_class("codec-tag")

        lbl = Gtk.Label(label=self.selected_codec)
        lbl.set_margin_start(8)
        lbl.set_margin_end(8)
        tag.append(lbl)

        btn_edit = Gtk.Button(icon_name="search-symbolic")
        btn_edit.set_has_frame(False)
        btn_edit.connect("clicked", self.on_change_codec_clicked)
        tag.append(btn_edit)

        self.codec_box.append(tag)

    def load_structured_template(self, template):
        data = template.get('data', {})
        self.entry_name.set_text(template['name'])

        if template['name']:
            self.entry_name.set_editable(False)
            self.entry_name.set_can_focus(False)

        if self.locked_type:
            try:
                idx = all_types.index(self.locked_type.lower())
                self.combo_type.set_selected(idx)
                self.combo_type.set_sensitive(False)
            except ValueError: pass
        else:
            try:
                idx = all_types.index(data.get('type', 'video').lower())
                self.combo_type.set_selected(idx)
            except ValueError: pass

        options = data.get('parameters', {}).get('options', {})
        for k, v in options.items():
            self.add_row_to_list(self.lst_encoder, k, v)

    def get_template_yaml_data(self):
        output = {
            "type": self.get_selected_type(),
            "codec": self.selected_codec,
            "parameters": {"options": {}},
            "filters": {
                "mode": self.combo_filter_mode.get_selected_item().get_string().lower(),
                "entries": []
            }
        }

        row = self.lst_encoder.get_first_child()
        while row:
            key = row._key_widget.get_label()
            if key != "Select...":
                output["parameters"]["options"][key] = self.extract_widget_value(row)
            row = row.get_next_sibling()

        return output

    def extract_widget_value(self, row):
        w = row._val_widget
        if isinstance(w, Gtk.DropDown):
            return w._tech_values[w.get_selected()]
        elif isinstance(w, Gtk.SpinButton):
            return w.get_value()
        elif isinstance(w, Gtk.Switch):
            return w.get_active()
        elif isinstance(w, Gtk.MenuButton):
            # Flag extraction logic
            active = [k for k, (cb, _) in w._check_buttons.items() if cb.get_active()]
            return "+".join(active)
        elif isinstance(w, Gtk.Entry):
            return w.get_text()
        return ""

    def get_selected_type(self):
        idx = self.combo_type.get_selected()
        return all_types[idx]

    def on_save_clicked(self, button):
        name = self.entry_name.get_text().strip()
        if not name:
            self.show_error_dialog("Name cannot be empty.")
            return

        yaml_data = self.get_template_yaml_data()

        if self.template['path']:
            save_path = Path(self.template['path'])
        else:
            base_dir = Path("./templates")
            base_dir.mkdir(exist_ok=True)
            save_path = base_dir / f"{name}.yaml"

        try:
            with open(save_path, 'w') as f:
                yaml.dump(yaml_data, f, sort_keys=False, indent=4)
            if self.on_save_callback:
                self.on_save_callback(name)
            self.destroy()
        except Exception as e:
            self.show_error_dialog(str(e))

    def show_error_dialog(self, message):
        dialog = Gtk.MessageDialog(
            transient_for=self, modal=True,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK, text=message
        )
        dialog.connect("response", lambda d, r: d.destroy())
        dialog.show()
