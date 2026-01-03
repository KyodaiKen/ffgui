import gi
gi.require_version("Gdk", "4.0")
from gi.repository import Gtk, Gio, Gdk

class SourceStreamRow(Gtk.ListBoxRow):
    def __init__(self, stream):
        super().__init__()
        self.stream = stream

        # Layout
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.set_child(hbox)

        # Left checkbox
        self.chk = Gtk.CheckButton()
        hbox.append(self.chk)

        # Label
        self.label = Gtk.Label(xalign=0)
        self.label.set_text(stream['codec_description'])
        hbox.append(self.label)