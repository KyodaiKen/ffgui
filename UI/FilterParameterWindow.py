import gi

from UI.Builder import Builder
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk
from UI.SinglePickerWindow import SinglePickerWindow

class FilterParameterWindow(Gtk.ApplicationWindow):
    def __init__(self, parent_window, filter_obj, current_values, on_save):
        super().__init__(title=f"Configure: {filter_obj['name']}", transient_for=parent_window, modal=True)
        self.set_default_size(500, 400)
        self.filter_obj = filter_obj
        self.on_save = on_save
        self.template_editor = parent_window # Reference for create_value_widget
        
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12, margin_start=12, margin_end=12, margin_top=12, margin_bottom=12)
        self.set_child(main_box)

        # Header with Add Button
        top_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        top_box.append(Gtk.Label(label="<b>Active Parameters</b>", use_markup=True, xalign=0, hexpand=True))
        
        btn_add = Gtk.Button(icon_name="list-add-symbolic", label="Add Parameter")
        btn_add.add_css_class("pill")
        btn_add.connect("clicked", self.on_add_param_clicked)
        top_box.append(btn_add)
        main_box.append(top_box)

        # Scrolled List of active params
        scroll = Gtk.ScrolledWindow(vexpand=True, has_frame=True)
        self.lst_params = Gtk.ListBox()
        self.lst_params.set_selection_mode(Gtk.SelectionMode.NONE)
        self.lst_params.add_css_class("boxed-list")
        scroll.set_child(self.lst_params)
        main_box.append(scroll)

        # Footer Actions
        btn_apply = Gtk.Button(label="Apply Changes")
        btn_apply.add_css_class("suggested-action")
        btn_apply.set_halign(Gtk.Align.END)
        btn_apply.connect("clicked", self._on_apply_clicked)
        main_box.append(btn_apply)

        # Load existing values
        for p_name, p_val in current_values.items():
            param_schema = next((p for p in filter_obj.get('parameters', []) if p['name'] == p_name), None)
            if param_schema:
                self.add_param_row(param_schema, p_val)

    def on_add_param_clicked(self, _):
        picker = SinglePickerWindow(
            parent_window = self,
            options = self.filter_obj.get("parameters", []),
            strings = {
                "title": f"Select a filter",
                "placeholder_text": "Search for a filter..."
            },
            item_filter = None,
            on_select = self.add_param_row
        )
        picker.present()

    def add_param_row(self, param_schema, value=None):
        # Prevent duplicates
        name = param_schema['name']
        existing = self.lst_params.get_first_child()
        while existing:
            if getattr(existing, "_param_name", None) == name:
                return 
            existing = existing.get_next_sibling()

        row_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10, margin_start=6, margin_end=6, margin_top=4, margin_bottom=4)
        
        name_lbl = Gtk.Label(label=name, xalign=0, width_request=100)
        name_lbl.add_css_class("caption-heading")
        
        # Reuse TemplateEditor logic for the widget
        val_widget = Builder.build_value_widget(self, name, value, schema=param_schema)
        val_widget.set_hexpand(True)

        btn_del = Gtk.Button(icon_name="user-trash-symbolic")
        
        row_box.append(name_lbl)
        row_box.append(val_widget)
        row_box.append(btn_del)
        
        row = Gtk.ListBoxRow(child=row_box)
        row._param_name = name
        row._val_widget = val_widget
        
        btn_del.connect("clicked", lambda _: self.lst_params.remove(row))
        self.lst_params.append(row)

    def _on_apply_clicked(self, _):
        results = {}
        row = self.lst_params.get_first_child()
        while row:
            if hasattr(row, "_param_name"):
                val = self.template_editor.extract_widget_value(row._val_widget)
                if val is not None and val != "":
                    results[row._param_name] = val
            row = row.get_next_sibling()
        
        self.on_save(results)
        self.destroy()