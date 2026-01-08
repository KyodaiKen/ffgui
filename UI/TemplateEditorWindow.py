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
            popover box { min-width: 180px; }
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
        lst.set_selection_mode(Gtk.SelectionMode.NONE)

        scroll.set_child(lst)
        box.append(scroll)
        container.append(box)
        return lst

    # --- WIDGET FACTORY ---

    def create_value_widget(self, key, value, schema):
        if not schema and key:
            params = self.get_codec_params_list()
            schema = next((p for p in params if p.get('name') == key), None)

        if not schema:
            return Gtk.Entry(text=str(value), hexpand=True)

        p_type = schema.get("type", "string")
        options = schema.get("options")

        # Handle Enums
        if p_type == "enum" and options:
            tech_values = [str(k) for k in options.keys()] if isinstance(options, dict) else [str(o) for o in options]
            choices = [f"{v.get('sdesc', k)} ({v.get('ldesc', '')})" for k, v in options.items()] if isinstance(options, dict) else tech_values

            w = Gtk.DropDown(model=Gtk.StringList.new(choices), hexpand=True)
            w._tech_values = tech_values
            if value:
                try: w.set_selected(tech_values.index(str(value)))
                except ValueError: pass
            return w

        # Handle Numeric
        if p_type in ["integer", "float"]:
            adj = Gtk.Adjustment(value=float(value or schema.get("default", 0)),
                                 lower=float(schema.get("min", -999999)),
                                 upper=float(schema.get("max", 999999)),
                                 step_increment=1.0 if p_type == "integer" else 0.1)
            w = Gtk.SpinButton(adjustment=adj, numeric=True)
            if p_type == "float": w.set_digits(2)
            return w

        # Handle Flags (Checkboxes in Popover)
        if p_type == "flags" and options:
            w = Gtk.MenuButton(label="None Selected", hexpand=True)
            popover = Gtk.Popover()
            vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            vbox.set_margin_start(8); vbox.set_margin_end(8); vbox.set_margin_top(8); vbox.set_margin_bottom(8)

            selected_flags = str(value).split("+") if value else []
            check_buttons = {}

            def on_flag_toggled(*_):
                active = [info['sdesc'] for k, (cb, info) in check_buttons.items() if cb.get_active()]
                w.set_label("+".join(active) if active else "None")

            for f_key, f_info in options.items():
                cb = Gtk.CheckButton(label=f_info.get('sdesc', f_key))
                cb.set_active(f_key in selected_flags)
                cb.connect("toggled", on_flag_toggled)
                vbox.append(cb)
                check_buttons[f_key] = (cb, f_info)

            popover.set_child(vbox)
            w.set_popover(popover)
            w._check_buttons = check_buttons
            on_flag_toggled()
            return w

        # Handle Boolean
        if p_type == "boolean":
            return Gtk.Switch(active=str(value).lower() in ['true', '1', 'on'], halign=Gtk.Align.START)

        return Gtk.Entry(text=str(value), hexpand=True)

    # --- ROW MANAGEMENT ---

    def add_row_to_list(self, listbox, key="", value="", schema=None):
        row_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        btn_key = Gtk.Button(label=key or "Select...", width_request=150)
        self.encoder_keys_group.add_widget(btn_key)

        if listbox == self.lst_encoder:
            btn_key.connect("clicked", self.on_encoder_picker_clicked)

        val_widget = self.create_value_widget(key, value, schema)
        btn_del = Gtk.Button(icon_name="user-trash-symbolic")

        row_box.append(btn_key)
        row_box.append(val_widget)
        row_box.append(btn_del)

        row = Gtk.ListBoxRow(child=row_box)
        row._key_widget, row._val_widget = btn_key, val_widget
        btn_del.connect("clicked", lambda *_: listbox.remove(row))
        listbox.append(row)

    # --- DATA FLOW ---

    def get_codec_params_list(self):
        all_codecs = self.app.ffmpeg_data.get('codecs', [])
        codec_obj = next((c for c in all_codecs if c['name'] == self.selected_codec), None)
        return codec_obj.get("parameters", []) if codec_obj else []

    def load_structured_template(self, template):
        data = template.get('data', {})
        self.entry_name.set_text(template['name'])
        if template['name']:
            self.entry_name.set_sensitive(False)

        target_type = self.locked_type or data.get('type', 'video')
        try:
            self.combo_type.set_selected(self.all_types.index(target_type.lower()))
            if self.locked_type: self.combo_type.set_sensitive(False)
        except ValueError: pass

        options = data.get('parameters', {}).get('options', {})
        for k, v in options.items():
            self.add_row_to_list(self.lst_encoder, k, v)

    # --- HANDLERS ---

    def on_add_encoder_param(self, _):
        def on_selected(k, s): self.add_row_to_list(self.lst_encoder, k, s)
        picker = EncoderParameterPickerWindow(self, self.selected_codec, self.get_selected_type(), self.get_codec_params_list(), on_selected)
        picker.present()

    def on_encoder_picker_clicked(self, button):
        row = button.get_parent().get_parent()
        def on_selected(k, s):
            button.set_label(k)
            row_box = row.get_child()
            row_box.remove(row._val_widget)
            new_w = self.create_value_widget(k, "", s)
            row_box.insert_child_after(new_w, button)
            row._val_widget = new_w

        picker = EncoderParameterPickerWindow(self, self.selected_codec, self.get_selected_type(), self.get_codec_params_list(), on_selected)
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

    def on_save_clicked(self, _):
        name = self.entry_name.get_text().strip()
        if not name: return

        options = {}
        row = self.lst_encoder.get_first_child()
        while row:
            key = row._key_widget.get_label()
            if key != "Select...":
                w = row._val_widget
                if isinstance(w, Gtk.DropDown): val = w._tech_values[w.get_selected()]
                elif isinstance(w, Gtk.SpinButton): val = w.get_value()
                elif isinstance(w, Gtk.Switch): val = w.get_active()
                elif isinstance(w, Gtk.MenuButton):
                    val = "+".join([k for k, (cb, _) in w._check_buttons.items() if cb.get_active()])
                else: val = w.get_text()
                options[key] = val
            row = row.get_next_sibling()

        # Save implementation...
        if self.on_save_callback: self.on_save_callback(name)
        self.destroy()

    def on_add_filter(self, _): pass
