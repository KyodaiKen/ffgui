import gi
gi.require_version("Gdk", "4.0")
gi.require_version("Gtk", "4.0")
from gi.repository import GLib, Gtk
from UI.MainWindow import MainWindow
from Core.Codec import Codec

class FFGuiApp(Gtk.Application):
    wndMain = None
    wndJobSetupWindow = None
    Jobs = {}

    def __init__(self, **kargs):
        super().__init__(application_id="com.kyo.ffgui", **kargs)
        GLib.set_application_name('ffGUI')
        self.wndMain = None

    def do_startup(self):
        Gtk.Application.do_startup(self)

    def do_activate(self):
        if not self.wndMain:
            self.wndMain = MainWindow(application=self)
        self.wndMain.present()

app = FFGuiApp()
app.run()