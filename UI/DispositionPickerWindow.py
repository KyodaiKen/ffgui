import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gdk

class DispositionTag(Gtk.Box):
    def __init__(self, text, on_remove_callback):
        # Set spacing to 0 and handle gaps with label margins
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.add_css_class("disposition-tag-pw") 
        self.text = text
        
        # CRITICAL: Prevent the tag from stretching to fill the row
        self.set_halign(Gtk.Align.START)

        lbl = Gtk.Label(label=text)
        lbl.set_margin_start(8)
        lbl.set_margin_end(4)
        self.append(lbl)

        # Use icon_name as a property here
        remove_btn = Gtk.Button(icon_name="window-close-symbolic")
        remove_btn.set_has_frame(False)
        remove_btn.set_valign(Gtk.Align.CENTER)
        
        # Ensure the button doesn't expand
        remove_btn.set_hexpand(False)
        
        remove_btn.connect("clicked", lambda _: on_remove_callback(self))
        self.append(remove_btn)

class DispositionPickerWindow(Gtk.ApplicationWindow):
    disposition_types = [
        "default", "alternative", "forced", "comment", "dub", 
        "original", "presentation", "visual_hearing", 
        "hearing_impaired", "captions", "metadata"
    ]

    def __init__(self, parent_window, current_val, on_select, **kwargs):
        super().__init__(**kwargs, title="Disposition Picker")
        self.on_select = on_select
        self.set_default_size(450, 550)
        self.set_transient_for(parent_window)
        self.set_modal(True)

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        main_box.set_margin_start(12)
        main_box.set_margin_end(12)
        main_box.set_margin_top(12)
        main_box.set_margin_bottom(12)
        self.set_child(main_box)

        # 1. Warning/Info Area
        self.info_label = Gtk.Label()
        self.info_label.set_markup(
            "<i><span size='small'>Note: Custom dispositions may cause FFmpeg errors if unsupported by the output container.</span></i>"
        )
        self.info_label.set_wrap(True)
        self.info_label.set_xalign(0)
        main_box.append(self.info_label)

        # 2. Selection Area
        selection_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        main_box.append(selection_hbox)

        self.lst_dispositions = Gtk.ListBox(hexpand=True)
        self.lst_dispositions.set_activate_on_single_click(False)
        
        scroll = Gtk.ScrolledWindow(vexpand=True)
        scroll.set_child(self.lst_dispositions)
        selection_hbox.append(scroll)

        for dt in self.disposition_types:
            self.lst_dispositions.append(Gtk.Label(label=dt, xalign=0, margin_start=6))

        btn_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.btn_add_plus = Gtk.Button(label="Add +")
        self.btn_add_minus = Gtk.Button(label="Add -")
        self.btn_add_plus.connect("clicked", self.on_add_clicked, "+")
        self.btn_add_minus.connect("clicked", self.on_add_clicked, "-")
        btn_box.append(self.btn_add_plus)
        btn_box.append(self.btn_add_minus)
        selection_hbox.append(btn_box)

        # 3. Custom Entry Area
        custom_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.ent_custom = Gtk.Entry(placeholder_text="Enter custom disposition...")
        self.ent_custom.set_hexpand(True)
        # Allow pressing 'Enter' in the custom box to add it
        self.ent_custom.connect("activate", lambda _: self.on_custom_add_clicked(None, "+"))
        
        btn_custom_add = Gtk.Button(label="Add Custom")
        btn_custom_add.connect("clicked", self.on_custom_add_clicked, "+")
        
        custom_hbox.append(self.ent_custom)
        custom_hbox.append(btn_custom_add)
        main_box.append(custom_hbox)

        # 4. Tag Container
        tag_frame = Gtk.Frame(label="Selected Dispositions")
        self.tag_flowbox = Gtk.FlowBox(
            orientation=Gtk.Orientation.HORIZONTAL,
            selection_mode=Gtk.SelectionMode.NONE,
            column_spacing=6,   # This sets your 6px horizontal gap
            row_spacing=6,      # This sets your 6px vertical gap
            homogeneous=False,  # Allow tags to have different widths
            halign=Gtk.Align.START,
            valign=Gtk.Align.START
        )
        self.tag_flowbox.set_margin_top(6)
        
        tag_frame.set_child(self.tag_flowbox)
        main_box.append(tag_frame)

        if current_val:
            for part in current_val.split(","):
                val = part.strip()
                if val: self.add_tag(val)

        # 5. Footer
        self.btn_ok = Gtk.Button(label="Apply")
        self.btn_ok.add_css_class("suggested-action")
        self.btn_ok.connect("clicked", self.on_ok_click)
        main_box.append(self.btn_ok)

    def add_tag(self, text):
        tag = DispositionTag(text, self.remove_tag)
        self.tag_flowbox.append(tag)

        child = self.tag_flowbox.get_last_child()
        if child:
            child.set_halign(Gtk.Align.START)
            child.set_valign(Gtk.Align.START)
            child.set_hexpand(False)

    def remove_tag(self, tag_widget):
        child = tag_widget.get_parent()
        self.tag_flowbox.remove(child)

    def on_add_clicked(self, button, prefix):
        selected_row = self.lst_dispositions.get_selected_row()
        if selected_row:
            label_text = selected_row.get_child().get_label()
            self.add_tag(f"{prefix}{label_text}")

    def on_custom_add_clicked(self, button, prefix):
        custom_text = self.ent_custom.get_text().strip()
        if custom_text:
            # Strip any +/- the user might have typed manually to avoid duplicates
            clean_text = custom_text.lstrip('+-')
            self.add_tag(f"{prefix}{clean_text}")
            self.ent_custom.set_text("") # Clear entry after adding

    def on_ok_click(self, button):
        tags = []
        child = self.tag_flowbox.get_first_child()
        while child:
            tag_widget = child.get_child()
            if isinstance(tag_widget, DispositionTag):
                tags.append(tag_widget.text)
            child = child.get_next_sibling()
        
        self.on_select(",".join(tags))
        self.destroy()