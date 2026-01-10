import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Pango

class FilterParameterPickerWindow(Gtk.ApplicationWindow):
    def __init__(self, parent_window, filter_obj, on_select):
        super().__init__(title=f"Add Parameter to {filter_obj['name']}", transient_for=parent_window, modal=True)
        self.set_default_size(400, 500)
        self.on_select = on_select
        
        header = Gtk.HeaderBar()
        self.set_titlebar(header)
        
        self.search_entry = Gtk.SearchEntry(placeholder_text="Search parameter name or description...")
        header.set_title_widget(self.search_entry)

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_child(main_box)

        scroll = Gtk.ScrolledWindow(vexpand=True)
        self.listbox = Gtk.ListBox()
        self.listbox.add_css_class("boxed-list")
        scroll.set_child(self.listbox)
        main_box.append(scroll)

        for p in filter_obj.get('parameters', []):
            row = Gtk.ListBoxRow()
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, margin_start=10, margin_end=10, margin_top=8, margin_bottom=8)
            
            row._param_data = p
            row._search_key = f"{p['name']} {p.get('descr', '')}".lower()

            name_lbl = Gtk.Label(label=f"<b>{p['name']}</b>", use_markup=True, xalign=0)
            descr_lbl = Gtk.Label(label=p.get('descr', 'No description'), xalign=0, wrap=True)
            descr_lbl.add_css_class("dim-label")
            
            box.append(name_lbl)
            box.append(descr_lbl)
            row.set_child(box)
            self.listbox.append(row)

        self.search_entry.connect("search-changed", lambda _: self.listbox.invalidate_filter())
        self.listbox.set_filter_func(self._filter_func)
        self.listbox.connect("row-activated", self._on_activated)
        self.search_entry.grab_focus()

    def _filter_func(self, row):
        txt = self.search_entry.get_text().lower()
        return not txt or txt in row._search_key

    def _on_activated(self, _, row):
        self.on_select(row._param_data)
        self.destroy()