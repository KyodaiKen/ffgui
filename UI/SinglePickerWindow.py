import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Pango

class SinglePickerWindow(Gtk.ApplicationWindow):
    def __init__(self, parent_window, options, strings, item_filter, on_select, **kwargs):
        super().__init__(**kwargs, title=strings.get('title', "Select Item"))
        
        self.on_select = on_select
        self.item_filter = item_filter
        self.set_default_size(450, 550)
        self.set_transient_for(parent_window)
        self.set_modal(True)

        self.options = options

        # UI Setup
        hb = Gtk.HeaderBar()
        self.set_titlebar(hb)
        
        self.search_entry = Gtk.SearchEntry(
            placeholder_text=strings.get('placeholder_text', "Search...")
        )
        self.search_entry.connect("search-changed", self.on_search_changed)
        hb.set_title_widget(self.search_entry)

        self.lst_items = Gtk.ListBox()
        self.lst_items.add_css_class("boxed-list")
        self.lst_items.set_filter_func(self.filter_rows)
        self.lst_items.connect("row-activated", self.on_row_activated)

        scroll = Gtk.ScrolledWindow(vexpand=True, margin_bottom=6, margin_end=6, margin_start=6, margin_top=6)
        scroll.set_child(self.lst_items)
        self.set_child(scroll)

        self.populate_list()
        self.search_entry.grab_focus()

    def populate_list(self):
        for item in self.options:
            if self.item_filter and not self.item_filter(item):
                continue
        
            row = Gtk.ListBoxRow()
            row._data = item
            
            # Quirk Mapping: Extract labels regardless of key names
            name = item.get('name')
            # Fallback chain for description: 'help' (encoders) -> 'descr' (filters) -> 'long_name' (containers)
            descr = item.get('descr') or item.get('long_name', "")

            row._search_key = f"{name} {descr}".lower()

            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4, 
                          margin_start=12, margin_end=12, margin_top=8, margin_bottom=8)
            
            header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True, spacing=6)
            
            lbl_key = Gtk.Label(xalign=0)
            lbl_key.set_markup(f"<b>{name}</b>")
            # This pushes everything else to the right
            lbl_key.set_hexpand(True) 
            header.append(lbl_key)
            
            if 'is_global' in item:
                type_text = "Global" if item['is_global'] else "Private"
                lbl_type = Gtk.Label(xalign=1) # Now xalign=1 works because the box is full width
                lbl_type.set_markup(f"<span alpha='70%'>[{type_text}]</span>")
                header.append(lbl_type)
            
            box.append(header)
            
            if descr:
                lbl_descr = Gtk.Label(label=descr, xalign=0)
                lbl_descr.add_css_class("caption")
                lbl_descr.add_css_class("dim-label")
                
                # --- DYNAMIC WRAPPING LOGIC ---
                lbl_descr.set_wrap(True)
                lbl_descr.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
                
                # This is the "Magic" line: 
                # It tells the label: "Your preferred width is small (e.g. 10 chars), 
                # but you can expand to fill the available space." 
                # This prevents the label from forcing the window wide.
                lbl_descr.set_width_chars(10) 
                
                # Ensure it expands to fill the Box width
                lbl_descr.set_hexpand(True)
                box.append(lbl_descr)

            row.set_child(box)
            self.lst_items.append(row)

    def filter_rows(self, row):
        search_text = self.search_entry.get_text().lower()
        return not search_text or search_text in row._search_key

    def on_search_changed(self, _):
        self.lst_items.invalidate_filter()

    def on_row_activated(self, _, row):
        self.on_select(row._data)
        self.destroy()