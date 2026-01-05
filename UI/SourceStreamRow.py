import gi
gi.require_version("Gdk", "4.0")
from gi.repository import Gtk, Pango

class SourceStreamRow(Gtk.ListBoxRow):
    def __init__(self, stream_descr, source_path, stream_index):
        super().__init__()
        self.source_path = source_path
        self.stream_index = stream_index

        # Layout
        grid = Gtk.Grid(orientation=Gtk.Orientation.VERTICAL, row_spacing=6, column_spacing=6)
        self.set_child(grid)

        # Left checkbox
        self.chk = Gtk.CheckButton()
        grid.attach(self.chk, 0, 0, 1, 1)

        # Label for stream
        self.lbl_strm = Gtk.Label(xalign=0, label=f"<b>{stream_descr}</b>", use_markup=True,)
        self.lbl_strm.set_ellipsize(Pango.EllipsizeMode.END)
        grid.attach(self.lbl_strm, 1, 0, 3, 1)

        # Label "Template"
        self.lbl_tpl = Gtk.Label(halign=Gtk.Align.END, label="Transcoding Template:")
        grid.attach(self.lbl_tpl, 1, 1, 1, 1)

        # Entry for template
        self.ent_tpl = Gtk.Entry(hexpand=True, halign=Gtk.Align.FILL)
        grid.attach(self.ent_tpl, 2, 1, 1, 1)

        # Button for search
        self.btn_srch = Gtk.Button(icon_name="search-symbolic", halign=Gtk.Align.END)
        grid.attach(self.btn_srch, 3, 1, 1, 1)

        # Label "Disposition"
        self.lbl_dsp = Gtk.Label(halign=Gtk.Align.END, label="Disposition:")
        grid.attach(self.lbl_dsp, 1, 2, 1, 1)

        # Entry for disposition
        self.ent_dsp = Gtk.Entry(hexpand=True, halign=Gtk.Align.FILL)
        grid.attach(self.ent_dsp, 2, 2, 1, 1)

        # Button for adding
        self.btn_add_dsp = Gtk.Button(icon_name="list-add", halign=Gtk.Align.END)
        grid.attach(self.btn_add_dsp, 3, 2, 1, 1)

        # Label "Language"
        self.lbl_lng = Gtk.Label(halign=Gtk.Align.END, label="Language:")
        grid.attach(self.lbl_lng, 1, 3, 1, 1)

        # Entry for language
        self.ent_lng = Gtk.Entry(hexpand=True, halign=Gtk.Align.FILL)
        grid.attach(self.ent_lng, 2, 3, 1, 1)

        # Button for search
        self.btn_srch_lng = Gtk.Button(icon_name="search-symbolic", halign=Gtk.Align.END)
        grid.attach(self.btn_srch_lng, 3, 3, 1, 1)