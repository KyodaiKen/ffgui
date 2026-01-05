import gi
gi.require_version("Gdk", "4.0")
from gi.repository import Gtk, Gio, Gdk, Pango

class DispositionPickerWindow(Gtk.ApplicationWindow):
    disposition_types = [
        "default",              # Marks the stream as the default for playback
        "alternative",          # Indicates an alternative stream that can be used
        "forced",               # Marks a stream as forced (e.g., subtitle that should always be shown)
        "comment",              # For streams that contain comments
        "dub",                  # A dubbed audio stream
        "original",             # Marks the original stream
        "presentation",         # For streams that are a presentation (like a primary video)
        "visual_hearing",       # For visually impaired audience
        "hearing_impaired",     # For hearing impaired audience
        "captions",             # For closed captions
        "metadata"              # For streams containing metadata
    ]

    def __init__(self, job, **kwargs):
        super().__init__(**kwargs, title="Disposition Picker")
