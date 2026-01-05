import gi
gi.require_version("Gdk", "4.0")
from gi.repository import Gtk, Gio, Gdk, Pango

class StreamTemplatePicker(Gtk.ApplicationWindow):
    def __init__(self, job, **kwargs):
        super().__init__(**kwargs, title="Stream Template Picker")