import gi
gi.require_version("Gdk", "4.0")
from gi.repository import Gtk, Pango
from Models.TemplateDataModel import TemplateDataModel
from UI.SinglePickerWindow import SinglePickerWindow
from UI.FilterParameterWindow import FilterParameterWindow
from UI.FilterGraphEditorWindow import FilterGraphEditorWindow
from UI.FlagsPickerWindow import FlagsPickerWindow
from UI.Builder import Builder
from UI.Icons import Icons
import copy

class TemplateEditorWindow(Gtk.ApplicationWindow):
    def __init__(self, parent_window, template, on_save_callback=None, locked_type=None, clone_mode=False, **kwargs):
        super().__init__(**kwargs, title="Template Editor")

        # State Initialization
        self.app = Gtk.Application.get_default()
        self.on_save_callback = on_save_callback
        self.locked_type = locked_type
        self.all_types = Icons.get_all_types()
        self.clone_mode = clone_mode

        # Template Setup
        self.template = self._prepare_template_data(template)
        self.selected_codec = self.template.get('codec', 'libx264')

        # Window Configuration
        self.set_default_size(1024, 700)
        self.set_transient_for(parent_window)
        self.set_modal(True)

        # Build UI
        self._build_ui()

        # Handle clone mode
        if self.clone_mode:
            self._apply_clone_mode_setup()

        # Fill Data
        self.load_structured_template(self.template)
        self.update_codec_ui()

    def _prepare_template_data(self, template):
        """Ensures the template is a flat dict for the editor, regardless of origin."""
        if template:
            # Create a copy so we don't mutate the original list object
            working_copy = copy.deepcopy(template)            
            return working_copy
            
        # Default flat structure for a brand new template
        return {
            "name": "", 
            "type": "video", 
            "codec": "libx264",
            "parameters": {"options": {}},
            "filters": {"mode": "simple", "entries": []}
        }

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
        
        # Container for Name + Badge
        name_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        name_vbox.append(self.entry_name)
        
        # Placeholder for badge
        self.badge_container = Gtk.Box()
        name_vbox.append(self.badge_container)

        grid.attach(Gtk.Label(label="Name:", halign=Gtk.Align.END), 0, 0, 1, 1)
        grid.attach(name_vbox, 1, 0, 1, 1)

        self.combo_type = Gtk.DropDown.new_from_strings([t.capitalize() for t in self.all_types])
        self.combo_type.props.halign = Gtk.Align.START
        self.combo_type.connect("notify::selected", self.on_type_changed)
        self.codec_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)

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

        self.param_name_group = Gtk.SizeGroup(mode=Gtk.SizeGroupMode.HORIZONTAL)

        # Footer Actions
        btn_save = Gtk.Button(label="Save Template")
        btn_save.add_css_class("suggested-action")
        btn_save.set_halign(Gtk.Align.END)
        btn_save.connect("clicked", self.on_save_clicked)
        main_box.append(btn_save)

    def _apply_clone_mode_setup(self):
            """Logic specific to cloning a template."""
            # Add the badge
            badge = Gtk.Label(label="Clone Mode: Please rename this template")
            badge.add_css_class("warning-badge")
            badge.set_halign(Gtk.Align.START)
            self.badge_container.append(badge)
            
            # Ensure name is editable in clone mode even if original was locked
            if not self.clone_mode:
                self.entry_name.set_editable(True)
                self.entry_name.set_can_focus(True)
            # Clear text or append suffix to prompt change
            current_text = self.entry_name.get_text()
            self.entry_name.set_text(f"{current_text}_copy")

    def _create_column(self, container, title, add_callback, is_filter=False):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6, hexpand=True)

        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        header.append(Gtk.Label(label=f"<b>{title}</b>", use_markup=True, xalign=0, hexpand=True))

        if is_filter:
            self.btn_add_filter = Gtk.Button(icon_name="list-add-symbolic")
            self.btn_add_filter.add_css_class("flat")
            self.btn_add_filter.connect("clicked", add_callback)
            header.append(self.btn_add_filter)
            box.append(header)

            mode_hbox = Gtk.Box(spacing=6)
            mode_hbox.append(Gtk.Label(label="Mode:"))
            self.combo_filter_mode = Gtk.DropDown.new_from_strings(["Simple", "Complex"])
            self.combo_filter_mode.connect("notify::selected", self.on_filter_mode_changed)
            mode_hbox.append(self.combo_filter_mode)
            box.append(mode_hbox)

            # The Stack allows us to swap the UI content
            self.filter_stack = Gtk.Stack()
            self.filter_stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
            
            # Page 1: Simple List
            scroll = Gtk.ScrolledWindow(vexpand=True)
            self.lst_filters = Gtk.ListBox()
            self.lst_filters.add_css_class("boxed-list")
            scroll.set_child(self.lst_filters)
            self.filter_stack.add_named(scroll, "simple")

            # Page 2: Complex Graph Preview
            graph_preview_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10, vexpand=True)
            graph_preview_box.add_css_class("graph-preview-area")
            
            self.graph_preview_img = Gtk.Image(icon_name="network-transmit-receive-symbolic", pixel_size=128, vexpand=True)
            graph_preview_box.append(self.graph_preview_img)
            
            btn_edit_graph = Gtk.Button(label="Edit Filter Graph")
            btn_edit_graph.add_css_class("pill")
            btn_edit_graph.connect("clicked", self.on_edit_graph_clicked)
            graph_preview_box.append(btn_edit_graph)
            
            self.filter_stack.add_named(graph_preview_box, "complex")
            
            box.append(self.filter_stack)
            container.append(box)
            return self.lst_filters
        else:
            self.btn_add_eo = Gtk.Button(icon_name="list-add-symbolic")
            self.btn_add_eo.add_css_class("flat")
            self.btn_add_eo.connect("clicked", add_callback)
            header.append(self.btn_add_eo)
            box.append(header)

        # Standard non-filter column logic
        scroll = Gtk.ScrolledWindow(vexpand=True)
        lst = Gtk.ListBox()
        lst.add_css_class("boxed-list")
        scroll.set_child(lst)
        box.append(scroll)
        container.append(box)
        return lst

    # --- ROW MANAGEMENT ---

    def add_row_to_list(self, listbox, param, value):
        row_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6, margin_top=4, margin_bottom=4, margin_end=4, margin_start=4)

        # 1. The Header (Key + Description)
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True, spacing=12)
        
        # Key Label
        lbl_key = Gtk.Label(xalign=0)
        lbl_key.set_markup(f"<span weight='bold' size='large'>{param['name']}</span>")
        
        # ADD TO SIZE GROUP: This ensures every 'lbl_key' across all rows 
        # has the same width, pushing the description to the same starting point.
        self.param_name_group.add_widget(lbl_key)
        
        # Description Label
        lbl_descr = Gtk.Label(label=param.get('descr', ''))
        lbl_descr.set_xalign(0)
        lbl_descr.add_css_class("caption")
        lbl_descr.add_css_class("dim-label")
        lbl_descr.set_wrap(True)
        lbl_descr.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
        lbl_descr.set_width_chars(10)
        lbl_descr.set_hexpand(True) # Take up the rest of the row
        
        header.append(lbl_key)
        header.append(lbl_descr)

        # 2. The Interaction Row (Widget + Delete Button)
        # To keep the UI compact, we often put the widget and delete button on the same line
        # but since you had them vertical, I'll follow your structure with a small fix.
        
        action_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        
        val_widget = Builder.build_value_widget(self, param['name'], value, param)
        val_widget.set_hexpand(True) # Make the entry/button fill the space
        
        btn_del = Gtk.Button(icon_name="user-trash-symbolic")
        btn_del.set_valign(Gtk.Align.CENTER)
        
        action_box.append(val_widget)
        action_box.append(btn_del)

        # Assembly
        row_box.append(header)
        row_box.append(action_box)

        row = Gtk.ListBoxRow(child=row_box)
        row._val_widget = val_widget
        row._key = param['name']

        btn_del.connect("clicked", lambda *_: listbox.remove(row))
        listbox.append(row)

    # --- HANDLERS ---

    def on_add_encoder_param(self, _):
        # Key = parameter name, Value = parameter object
        params_dict = {}
        ffmpeg_data = getattr(self.app, 'ffmpeg_data', {})
        
        # 1. ADD GLOBALS FIRST (Lower Priority)
        groups = ffmpeg_data.get('globals', [])
        for group in groups:
            group_name = group.get("name", "").lower()
            for p in group.get("parameters", []):
                p_entry = p.copy()
                p_entry['is_global'] = True
                p_entry['group_name'] = group_name
                # If this name exists, it gets stored.
                params_dict[p['name']] = p_entry

        # 2. ADD CODEC-SPECIFIC SECOND (Higher Priority)
        codecs = ffmpeg_data.get('codecs', [])
        current_codec_data = next((c for c in codecs if c['name'] == self.selected_codec), {})
        
        for p in current_codec_data.get('parameters', []):
            p_entry = p.copy()
            p_entry['is_global'] = False
            # OVERWRITE: If the name already exists in params_dict from the Globals step,
            # this codec-specific p_entry replaces it entirely.
            params_dict[p['name']] = p_entry

        # Convert the deduplicated, prioritized dict back to a list
        params = list(params_dict.values())

        # Sort
        params.sort(key=lambda x: (x['is_global'], x['name'].lower()))

        stream_type = self.get_selected_type()

        def is_parameter_allowed(param):
            ctx = param.get("context", {})
            is_av_opt = param.get('group_name') == "av_options"
            
            return (
                (stream_type == "video" and ctx.get("video")) or
                (stream_type == "audio" and ctx.get("audio")) or
                (stream_type == "subtitle" and ctx.get("subtitle")) or
                is_av_opt
            )
        
        def on_selected(p_entry):
            self.add_row_to_list(self.lst_encoder, p_entry, value=None)

        picker = SinglePickerWindow(
            parent_window = self,
            options = params,
            strings = {
                "title": f"Select {self.selected_codec} codec parameter to add",
                "placeholder_text": "Search for a parameter..."
            },
            item_filter = is_parameter_allowed,
            on_select = on_selected
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
        def on_select_codec(codec):
            setattr(self, 'selected_codec', codec.get("name", ""))
            self.update_codec_ui()

        # Access the application instance to get the cached JSON data
        ffmpeg_data = getattr(self.app, 'ffmpeg_data', {})
        codecs_list = ffmpeg_data.get('codecs', [])

        codecs_dict = {}
        for codec in codecs_list:
            c = codec.copy()
            codecs_dict[c['name']] = c

        # Always add the copy option
        codecs_dict['copy'] = {
            "name": "copy",
            "descr": "Copy (no transcoding)",
            "flags": {},
            "parameters": []
        }

        # Convert the deduplicated, prioritized dict back to a list
        codecs = list(codecs_dict.values())

        # Sort
        codecs.sort(key=lambda x: (x['name'].lower()))

        stream_type = self.get_selected_type()

        def is_parameter_allowed(codec):
            flags = codec.get("flags", {})
            
            return (
                ((stream_type == "video" and flags.get("video")) or
                (stream_type == "audio" and flags.get("audio")) or
                (stream_type == "subtitle" and flags.get("subtitle")) and
                flags.get("encoder"))
            )
        
        picker = SinglePickerWindow(
            parent_window = self,
            options = codecs,
            strings = {
                "title": f"Select a codec",
                "placeholder_text": "Search for a codec..."
            },
            item_filter = is_parameter_allowed,
            on_select = on_select_codec
        )
        picker.present()

    def on_type_changed(self, *args):
        self.template['type'] = self.get_selected_type()

    def get_selected_type(self):
        return self.all_types[self.combo_type.get_selected()]

    def load_structured_template(self, template):
        # 1. Handle Name
        name = template.get('name', '')
        self.entry_name.set_text(name)

        if name != "New Template" and not self.clone_mode:
            self.entry_name.set_editable(False)
            self.entry_name.set_can_focus(False)
        else:
            # Ensure it is explicitly enabled for new/cloned templates
            self.entry_name.set_editable(True)
            self.entry_name.set_can_focus(True)

        # 2. Data is now guaranteed to be flat thanks to _prepare_template_data
        self.selected_codec = template.get('codec', 'libx264')

        # 3. Update Type Dropdown
        target_type = self.locked_type or template.get('type', 'video')
        try:
            idx = [t.lower() for t in self.all_types].index(target_type.lower())
            self.combo_type.set_selected(idx)
        except (ValueError, AttributeError):
            pass

        # 4. Filter Mode
        if hasattr(self, 'combo_filter_mode'):
            f_data = template.get('filters', {})
            f_mode = f_data.get('mode', 'simple').lower()
            # Match "simple" or "complex" to the dropdown index
            self.combo_filter_mode.set_selected(1 if f_mode == "complex" else 0)

        # 5. Clear and Add Encoder rows
        self.lst_encoder.remove_all() # GTK4 convenience method

        def get_full_parameter_map():
            """Returns a dict of {name: param_object} prioritized by Codec > Global."""
            param_map = {}
            ffmpeg_data = getattr(self.app, 'ffmpeg_data', {})
            
            # 1. Globals (Lower Priority)
            for group in ffmpeg_data.get('globals', []):
                group_name = group.get("name", "").lower()
                for p in group.get("parameters", []):
                    p_entry = p.copy()
                    p_entry['is_global'] = True
                    p_entry['group_name'] = group_name
                    param_map[p['name']] = p_entry

            # 2. Codec-Specific (Higher Priority)
            codecs = ffmpeg_data.get('codecs', [])
            current_codec_data = next((c for c in codecs if c['name'] == self.selected_codec), {})
            for p in current_codec_data.get('parameters', []):
                p_entry = p.copy()
                p_entry['is_global'] = False
                param_map[p['name']] = p_entry
            
            return param_map
            
        full_map = get_full_parameter_map()

        params = template.get('parameters', {}).get('options', {})
        for k, v in params.items():
            # Find the rich parameter object from FFmpeg data
            if k in full_map:
                param_obj = full_map[k]
            else:
                # Fallback if the parameter name isn't recognized by current FFmpeg
                param_obj = {
                    'name': k, 
                    'descr': "Unknown parameter (not found in current FFmpeg data)",
                    'is_global': False 
                }
            
            # Pass the rich object (param_obj) instead of just the string (k)
            self.add_row_to_list(self.lst_encoder, param_obj, value=v)

        # 6. Load Filter rows
        self.lst_filters.remove_all()
        f_entries = template.get('filters', {}).get('entries', [])
        all_ffmpeg_filters = getattr(self.app, 'ffmpeg_data', {}).get('filters', [])
        
        for entry in f_entries:
            name = entry.get('name')
            params = entry.get('params', {})
            # Find the full filter schema from ffmpeg_data
            f_obj = next((f for f in all_ffmpeg_filters if f['name'] == name), None)
            if f_obj:
                self.add_filter_row(f_obj, params)

    def show_error_dialog(self, message):
        """Standard GTK4 Message Dialog helper."""
        dialog = Gtk.AlertDialog(message=message)
        dialog.show(self)

    def _get_options_from_rows(self):
        """Iterates through the ListBox and collects key-value pairs."""
        options = {}
        row = self.lst_encoder.get_first_child()
        while row:
            # GTK ListBox rows might contain separators or focus placeholders
            if hasattr(row, "_val_widget"):
                options[row._key] = self.extract_widget_value(row._val_widget)
            row = row.get_next_sibling()
        return options

    def on_save_clicked(self, _):
        filename = self.entry_name.get_text().strip()
        if not filename:
            self.show_error_dialog("Template name cannot be empty.")
            return

        options = self._get_options_from_rows()

        # Gather filters
        filter_entries = []
        f_row = self.lst_filters.get_first_child()
        while f_row:
            if hasattr(f_row, "_filter_obj"):
                filter_entries.append({
                    "name": f_row._filter_obj['name'],
                    "params": f_row._filter_params
                })
            f_row = f_row.get_next_sibling()
        
        # Construct technical data
        yaml_data = {
            "type": self.get_selected_type(),
            "codec": self.selected_codec,
            "parameters": {"options": options},
            "filters": {
                "mode": self.combo_filter_mode.get_selected_item().get_string().lower() if hasattr(self, 'combo_filter_mode') else "simple",
                "entries": filter_entries
            }
        }

        try:
            # Use the directory provided by the main application object
            TemplateDataModel.save_template(self.app.templates_dir, filename, yaml_data)
            
            if self.on_save_callback:
                self.on_save_callback(filename)
            self.destroy()
        except Exception as e:
            self.show_error_dialog(f"Save failed: {str(e)}")

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
            return 1 if w.get_active() else 0

        elif isinstance(w, Gtk.Entry):
            return w.get_text()

        elif isinstance(w, Gtk.MenuButton) and hasattr(w, "_check_buttons"):
            # Flag extraction
            active = [k for k, (cb, _) in w._check_buttons.items() if cb.get_active()]
            return "+".join(active)

        return ""

    def on_filter_mode_changed(self, combo, _):
        mode = "complex" if combo.get_selected() == 1 else "simple"
        self.filter_stack.set_visible_child_name(mode)
        if mode == "complex":
            self.btn_add_filter.set_visible(False)
        else:
            self.btn_add_filter.set_visible(True)

    def on_edit_graph_clicked(self, _):
        # We pass the current template data to the graph editor
        editor = FilterGraphEditorWindow(self, self.template.get('filters', {}))
        editor.present()

    def on_add_filter(self, _):
        def on_filter_selected(filter):
            # Immediately open the parameter config for the chosen filter
            self.open_filter_config(filter, {})

        app = Gtk.Application.get_default()
        all_filters = getattr(app, 'ffmpeg_data', {}).get('filters', [])
        
        filters_dict = {}
        for filter in all_filters:
            f = filter.copy()
            filters_dict[f['name']] = f

        all_filters = list(filters_dict.values())
        all_filters.sort(key=lambda x: (x['name'].lower()))

        def is_parameter_allowed(filter):
            return not filter.get("is_complex", False)
        
        picker = SinglePickerWindow(
            parent_window = self,
            options = all_filters,
            strings = {
                "title": f"Select a filter",
                "placeholder_text": "Search for a filter..."
            },
            item_filter = is_parameter_allowed,
            on_select = on_filter_selected
        )

        picker.present()

    def open_filter_config(self, filter_obj, current_params, existing_row=None):
        def on_params_saved(new_params):
            if existing_row:
                # Update existing data
                existing_row._filter_params = new_params
                self._update_filter_row_label(existing_row)
            else:
                # Add as new row
                self.add_filter_row(filter_obj, new_params)

        editor = FilterParameterWindow(self, filter_obj, current_params, on_params_saved)
        editor.present()

    def add_filter_row(self, filter_obj, params):
        row_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        
        # Label showing filter name and summary
        lbl_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True)
        name_lbl = Gtk.Label(label=f"<b>{filter_obj['name']}</b>", use_markup=True, xalign=0)
        lbl_box.append(name_lbl)
        
        row = Gtk.ListBoxRow(child=row_box)
        row._filter_obj = filter_obj
        row._filter_params = params
        
        # Summary label for params
        row._summary_lbl = Gtk.Label(xalign=0, ellipsize=Pango.EllipsizeMode.END)
        row._summary_lbl.add_css_class("dim-label")
        lbl_box.append(row._summary_lbl)
        row_box.append(lbl_box)

        # Config Button
        btn_cfg = Gtk.Button(icon_name="emblem-system-symbolic")
        btn_cfg.connect("clicked", lambda _: self.open_filter_config(row._filter_obj, row._filter_params, row))
        
        # Delete Button
        btn_del = Gtk.Button(icon_name="user-trash-symbolic")
        btn_del.connect("clicked", lambda _: self.lst_filters.remove(row))

        row_box.append(btn_cfg)
        row_box.append(btn_del)
        
        self._update_filter_row_label(row)
        self.lst_filters.append(row)

    def _update_filter_row_label(self, row):
        """Creates a string like 'w=1280:h=720' for the UI summary."""
        summary = ":".join([f"{k}={v}" for k, v in row._filter_params.items()])
        row._summary_lbl.set_text(summary or "(no parameters)")
