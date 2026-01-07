import gi
gi.require_version("Gdk", "4.0")
from gi.repository import Gtk, Pango
from UI.MetadataManagerWindow import MetadataManagerWindow
from UI.DispositionPickerWindow import DispositionPickerWindow
from UI.LanguagePickerWindow import LanguagePickerWindow

class SourceStreamRow(Gtk.ListBoxRow):
    def __init__(self, stream_descr, stream_type, source_path, stream_index, parent_window, initial_metadata):
        super().__init__()
        self.source_path = source_path
        self.stream_type = stream_type
        self.stream_index = stream_index
        self.parent_window = parent_window
        self.stream_metadata = initial_metadata if initial_metadata is not None else {}

        # Layout
        grid = Gtk.Grid(orientation=Gtk.Orientation.VERTICAL, row_spacing=6, column_spacing=6)
        self.set_child(grid)

        # Left checkbox
        self.chk = Gtk.CheckButton()
        grid.attach(self.chk, 0, 0, 1, 1)

        # Label for stream
        self.lbl_strm = Gtk.Label(xalign=0, label=f"<b>{stream_descr}</b>", use_markup=True,)
        self.lbl_strm.set_ellipsize(Pango.EllipsizeMode.END)
        grid.attach(self.lbl_strm, 1, 0, 2, 1)

        # Tag button for stream meta data
        self.btn_meta = Gtk.Button(icon_name="tag-symbolic", halign=Gtk.Align.END, tooltip_text="Setup Stream Metadata")
        self.btn_meta.set_margin_end(24)
        grid.attach(self.btn_meta, 3, 0, 1, 1) 
        self.btn_meta.connect("clicked", self.on_manage_meta)
        # Highlight button if metadata exists initially
        self.update_meta_button_style()

        # Label "Template"
        self.lbl_tpl = Gtk.Label(halign=Gtk.Align.END, label="Transcoding Template:")
        grid.attach(self.lbl_tpl, 1, 1, 1, 1)

        # Entry for template
        self.ent_tpl = Gtk.Entry(hexpand=True, halign=Gtk.Align.FILL)
        self.ent_tpl.set_editable(False)
        self.ent_tpl.set_can_focus(False)
        grid.attach(self.ent_tpl, 2, 1, 1, 1)

        # Button for search
        self.btn_srch = Gtk.Button(icon_name="search-symbolic", halign=Gtk.Align.END)
        self.btn_srch.set_margin_end(24)
        self.btn_srch.connect("clicked", self.on_search_tpl_click)
        grid.attach(self.btn_srch, 3, 1, 1, 1)

        # Label "Disposition"
        self.lbl_dsp = Gtk.Label(halign=Gtk.Align.END, label="Disposition:")
        grid.attach(self.lbl_dsp, 1, 2, 1, 1)

        # Entry for disposition
        self.ent_dsp = Gtk.Entry(hexpand=True, halign=Gtk.Align.FILL)
        grid.attach(self.ent_dsp, 2, 2, 1, 1)

        # Button for adding
        self.btn_add_dsp = Gtk.Button(icon_name="search-symbolic", halign=Gtk.Align.END)
        self.btn_add_dsp.set_margin_end(24)
        grid.attach(self.btn_add_dsp, 3, 2, 1, 1)
        self.btn_add_dsp.connect("clicked", self.on_add_dsp_click)

        # Label "Language"
        self.lbl_lng = Gtk.Label(halign=Gtk.Align.END, label="Language:")
        grid.attach(self.lbl_lng, 1, 3, 1, 1)

        # Entry for language
        self.ent_lng = Gtk.Entry(hexpand=True, halign=Gtk.Align.FILL)
        grid.attach(self.ent_lng, 2, 3, 1, 1)

        # Button for search
        self.btn_srch_lng = Gtk.Button(icon_name="search-symbolic", halign=Gtk.Align.END)
        self.btn_srch_lng.set_margin_end(24)
        grid.attach(self.btn_srch_lng, 3, 3, 1, 1)
        self.btn_srch_lng.connect("clicked", self.on_search_lng_click)

    def on_add_dsp_click(self, button):
        # We pass a 'on_select' function to the picker
        self.pw = DispositionPickerWindow(
            self.parent_window,
            self.ent_dsp.get_text(),
            on_select=self.apply_disposition # New callback
        )
        self.pw.present()

    def apply_disposition(self, selected_text):
        self.ent_dsp.set_text(selected_text)

    def on_search_lng_click(self, button):
        # We pass the callback exactly like we did for the Disposition picker
        self.pw = LanguagePickerWindow(
            parent_window = self.parent_window,
            current_val=self.ent_lng.get_text(),
            on_select=self.apply_language
        )
        self.pw.present()

    def apply_language(self, selected_code):
        self.ent_lng.set_text(selected_code)

    def update_meta_button_style(self):
        if self.stream_metadata:
            self.btn_meta.add_css_class("suggested-action")
        else:
            self.btn_meta.remove_css_class("suggested-action")

    def on_manage_meta(self, _):
        win = MetadataManagerWindow(self.parent_window, self.stream_metadata, self.save_meta)
        win.present()

    def save_meta(self, meta):
        self.stream_metadata = meta
        self.update_meta_button_style()

    def on_search_tpl_click(self, button):
        from UI.TemplatePickerWindow import TemplatePickerWindow
        self.pw = TemplatePickerWindow(
            parent_window=self.parent_window,
            current_val=self.ent_tpl.get_text(),
            stream_type=self.stream_type,
            on_select=self.apply_template
        )
        self.pw.present()

    def apply_template(self, template_name):
        self.ent_tpl.set_text(template_name)