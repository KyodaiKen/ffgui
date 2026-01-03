import gi
gi.require_version("Gdk", "4.0")
from gi.repository import Gtk, Gio, Gdk
from UI.SourceStreamRow import SourceStreamRow

import av

class JobSetupWindow(Gtk.ApplicationWindow):
    def __init__(self, job, **kwargs):
        super().__init__(**kwargs, title="Job Setup")
        self.job = job

        # Set window size
        self.set_size_request(640, 480)

        # Main box of our window
        self.box_outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, vexpand=True, spacing=6)
        self.box_outer.props.margin_start = 6
        self.box_outer.props.margin_end = 6
        self.box_outer.props.margin_top = 6
        self.box_outer.props.margin_bottom = 6
        self.set_child(self.box_outer)

        # Create a Group Box
        self.frm_src = Gtk.Frame()
        self.frm_src.set_label_widget(Gtk.Label(label="Source", ))

        # Create the list box
        self.listbox = Gtk.ListBox(vexpand=True)
        self.listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        
        for s in self.job.SourceStreams:
            stream = self.job.SourceStreams[s]
            row = SourceStreamRow(stream)
            self.listbox.append(row)

        self.frm_src.set_child(self.listbox)

        # Add the notebook to the main window
        self.box_outer.append(self.frm_src)
