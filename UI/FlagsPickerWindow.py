import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Pango, GLib

class FlagsPickerWindow(Gtk.ApplicationWindow):
    def __init__(self, parent, options, current_values, strings, on_apply, **kwargs):
        super().__init__(**kwargs, title=strings['title'])
        self.on_apply = on_apply
        self.set_default_size(450, 600)
        self.set_transient_for(parent)
        self.set_modal(True)
        
        # Convert current_values (e.g., "default+forced" or ["default", "forced"]) to a set for fast lookup
        if isinstance(current_values, str):
            self.active_flags = set(current_values.split(','))
        else:
            self.active_flags = set(current_values or [])

        self.options = options
        self.check_widgets = {} # Map flag name -> CheckButton

        # UI Setup
        hb = Gtk.HeaderBar()
        self.set_titlebar(hb)
        
        # Add Apply Button to HeaderBar
        btn_apply = Gtk.Button(label="Apply")
        btn_apply.add_css_class("suggested-action")
        btn_apply.connect("clicked", self.on_apply_clicked)
        hb.pack_end(btn_apply)

        self.search_entry = Gtk.SearchEntry(placeholder_text=strings['placeholder_text'])
        self.search_entry.connect("search-changed", self.on_search_changed)
        hb.set_title_widget(self.search_entry)

        self.lst_params = Gtk.ListBox()
        self.lst_params.add_css_class("boxed-list")
        self.lst_params.set_selection_mode(Gtk.SelectionMode.NONE) # Use checkboxes instead of selection
        self.lst_params.set_filter_func(self.filter_rows)
        # Clicking the row toggles the checkbox
        self.lst_params.connect("row-activated", self.on_row_activated)

        scroll = Gtk.ScrolledWindow(vexpand=True)
        scroll.set_child(self.lst_params)
        self.set_child(scroll)

        self.create_list_widgets()

    def create_list_widgets(self):
        for opt in self.options:
            name = opt['name']
            row = Gtk.ListBoxRow()
            row._search_key = f"{name} {opt.get('descr', '')}".lower()

            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12, 
                          margin_start=12, margin_end=12, margin_top=8, margin_bottom=8)
            
            # Checkbox for multi-select
            chk = Gtk.CheckButton()
            chk.set_active(name in self.active_flags)
            chk.set_can_focus(False) # Row activation handles this
            self.check_widgets[name] = chk
            
            text_vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            lbl_key = Gtk.Label(label=f"<b>{name}</b>", xalign=0, use_markup=True)
            lbl_help = Gtk.Label(label=opt.get('descr', ''), xalign=0, wrap=True)
            lbl_help.add_css_class("caption")
            
            text_vbox.append(lbl_key)
            text_vbox.append(lbl_help)
            
            box.append(chk)
            box.append(text_vbox)
            row.set_child(box)
            self.lst_params.append(row)

    def on_row_activated(self, listbox, row):
        # Find the checkbox in this row and toggle it
        # We find it via the name stored in the schema
        # Or more simply, just look at the row's child
        box = row.get_child()
        chk = box.get_first_child() # The CheckButton is the first child in the box
        chk.set_active(not chk.get_active())

    def on_apply_clicked(self, btn):
        # Extract names of all checked buttons
        selected = [name for name, chk in self.check_widgets.items() if chk.get_active()]
        # Return the list or joined string
        self.on_apply(selected)
        self.destroy()

    def filter_rows(self, row):
        search_text = self.search_entry.get_text().lower()
        return not search_text or search_text in row._search_key

    def on_search_changed(self, entry):
        self.lst_params.invalidate_filter()