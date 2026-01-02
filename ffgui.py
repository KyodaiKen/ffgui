import gi
gi.require_version("Gdk", "4.0")
gi.require_version("Gtk", "4.0")
from gi.repository import GLib, Gtk
from Windows.MainWindow import MainWindow
from Core.Codec import Codec

class FFGuiApp(Gtk.Application):
    def __init__(self, **kargs):
        super().__init__(application_id="com.kyo.ffgui", **kargs)
        GLib.set_application_name('ffGUI')
        self.window = None

    def do_startup(self):
        Gtk.Application.do_startup(self)

        # Test codec yaml
        c = Codec()
        c.from_yaml("Codecs/FLAC.yaml")
        print(vars(c))

    def do_activate(self):
        if not self.window:
            self.window = MainWindow(application=self)
            self.window.set_size_request(640,480)
        self.window.present()

app = FFGuiApp()
app.run()