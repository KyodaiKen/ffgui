import gi
gi.require_version("Gdk", "4.0")
from gi.repository import Gtk, Gio, Gdk

import av

class JobSetupWindow(Gtk.ApplicationWindow):
    def __init__(self, **kargs):
        super().__init__(**kargs, title="Job Setup")

        # Set window size
        self.set_default_size(640, 480)

        # Main box of our window
        box_outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, vexpand=True, spacing=2)
        box_outer.props.margin_start = 6
        box_outer.props.margin_end = 6
        box_outer.props.margin_top = 6
        box_outer.props.margin_bottom = 6
        self.set_child(box_outer)

        # Create a Notebook widget
        notebook = Gtk.Notebook(vexpand=True)

        # Create the first tab content
        tab1_content = Gtk.Box()

        # Add the first tab to the notebook
        notebook.append_page(tab1_content, Gtk.Label(label="Sources"))

        # Create the second tab content
        tab2_content = Gtk.Box()

        # Add the second tab to the notebook
        notebook.append_page(tab2_content, Gtk.Label(label="Destination"))

        # Add the notebook to the main window
        box_outer.append(notebook)
