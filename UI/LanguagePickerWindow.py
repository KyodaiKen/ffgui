import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gio, Gdk, Pango, GLib
import pycountry

class LanguagePickerWindow(Gtk.ApplicationWindow):
    def __init__(self, parent_window, current_val, on_select, **kwargs):
        super().__init__(**kwargs, title="Select Language")
        self.on_select = on_select
        self.set_default_size(450, 500)
        self.set_transient_for(parent_window)
        self.set_modal(True)
        
        # Internal state
        self.current_val = current_val.lower() if current_val else ""
        self.languages = list(pycountry.languages)
        self._target_row = None

        # Header Bar
        hb = Gtk.HeaderBar()
        self.set_titlebar(hb)

        self.search_entry = Gtk.SearchEntry(placeholder_text="Search language...")
        self.search_entry.set_max_width_chars(30)
        self.search_entry.connect("search-changed", self.on_search_changed)
        # Close/Select on Enter
        self.search_entry.connect("activate", lambda e: self.on_ok_clicked(None))
        hb.set_title_widget(self.search_entry)

        # Main Layout
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        main_box.set_margin_start(12)
        main_box.set_margin_end(12)
        main_box.set_margin_top(12)
        main_box.set_margin_bottom(12)
        self.set_child(main_box)

        # Scrollable ListBox
        self.lst_languages = Gtk.ListBox()
        self.lst_languages.add_css_class("boxed-list")
        self.lst_languages.set_selection_mode(Gtk.SelectionMode.SINGLE)

        # Disable single-click activation to ensure we need a double-click
        self.lst_languages.set_activate_on_single_click(False)

        # Trigger selection when a row is double-clicked or 'Enter' is pressed
        self.lst_languages.connect("row-activated", self.on_row_activated)
        
        self.scroll = Gtk.ScrolledWindow(vexpand=True)
        self.scroll.set_child(self.lst_languages)
        main_box.append(self.scroll)

        # OK Button
        self.btn_ok = Gtk.Button(label="Select Language")
        self.btn_ok.add_css_class("suggested-action")
        self.btn_ok.connect("clicked", self.on_ok_clicked)
        main_box.append(self.btn_ok)

        self.populate_list()
        self.scroll_to_selected()

        # Put the cursor in the search box so the user can type immediately
        self.search_entry.grab_focus()

    def populate_list(self, filter_text=""):
        while child := self.lst_languages.get_first_child():
            self.lst_languages.remove(child)

        filter_text = filter_text.lower().strip()
        matches = []
        
        # Find the current language object immediately to ensure it's included
        current_lang_obj = None
        if self.current_val:
            # We search the full list once for the actual object
            current_lang_obj = next((l for l in self.languages if getattr(l, "alpha_3", "").lower() == self.current_val), None)

        # Build the display list
        for lang in self.languages:
            code = getattr(lang, "alpha_3", "").lower()
            name = getattr(lang, "name", "").lower()
            
            is_current = (code == self.current_val)
            is_match = not filter_text or (filter_text in code or filter_text in name)

            if is_match or is_current:
                rank = 3
                if filter_text == code: rank = 0
                elif filter_text == name: rank = 1
                elif code.startswith(filter_text) or name.startswith(filter_text): rank = 2
                
                # If it's the current selection, we give it the highest priority (rank -1)
                # so it's ALWAYS at the very top of the list when opening.
                if is_current and not filter_text:
                    rank = -1

                matches.append({
                    "code": code,
                    "name": getattr(lang, "name", "Unknown"),
                    "rank": rank,
                    "is_current": is_current
                })

        # Sort: Rank first, then alphabetical Name
        matches.sort(key=lambda x: (x["rank"], x["name"]))

        self._target_row = None
        # We take 100 results, but our rank -1 ensures 'current' is in this slice
        for item in matches[:100]:
            row = Gtk.ListBoxRow()
            hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=15)
            hbox.set_margin_start(10)
            hbox.set_margin_end(10)
            hbox.set_margin_top(6)
            hbox.set_margin_bottom(6)
            
            lbl_code = Gtk.Label(xalign=0)
            lbl_code.set_markup(f"<b>{item['code']}</b>")
            lbl_code.set_width_chars(5) 
            
            lbl_name = Gtk.Label(label=item['name'], xalign=0)
            lbl_name.set_ellipsize(Pango.EllipsizeMode.END)
            lbl_name.set_hexpand(True)
            
            hbox.append(lbl_code)
            hbox.append(lbl_name)
            row.set_child(hbox)
            row._code = item['code']
            
            self.lst_languages.append(row)
            
            if item['is_current']:
                self._target_row = row

    def scroll_to_selected(self):
        if self._target_row:
            self.lst_languages.select_row(self._target_row)
            self._target_row.grab_focus()
            self.lst_languages.set_focus_child(self._target_row)
        return False

    def scroll_to_selected(self):
        if self._target_row:
            self.lst_languages.select_row(self._target_row)
            self._target_row.grab_focus()
            self.lst_languages.set_focus_child(self._target_row)
        return False

    def on_search_changed(self, entry):
        self.populate_list(entry.get_text())
        # We don't want to auto-scroll while the user is actively typing a search
        # so we don't call scroll_to_selected here.

    def on_ok_clicked(self, button):
        selected = self.lst_languages.get_selected_row()
        if selected:
            self.on_select(selected._code.lower())
        self.destroy()

    def on_row_activated(self, listbox, row):
            """Called on double-click or Enter key"""
            if row and hasattr(row, "_code"):
                self.on_select(row._code.lower())
                self.destroy()