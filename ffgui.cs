using Gtk;
using Gio;
using Gdk;
using System.Runtime.InteropServices;

// Use the standard Gtk.Application
var app = Gtk.Application.New("de.kyo.ffgui", Gio.ApplicationFlags.FlagsNone);

app.OnActivate += (sender, e) =>
{
#if WINDOWS
    var display = Display.GetDefault();
    if (display != null)
    {
        // 1. Detect Windows Theme (Simple version)
        // You can add a Registry check later, for now we assume 'dark'
        string subfolder = "dark";

        var iconTheme = Gtk.IconTheme.GetForDisplay(Gdk.Display.GetDefault()!);

        // Add the hicolor icons
        string iconDir = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "gtk-icons");
        if (Directory.Exists(iconDir))
            iconTheme.AddSearchPath(iconDir);

        // Add the theme assets specifically (if they are used as icons)
        string assetDir = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "share", "themes", subfolder, "gtk-4.0", "assets");
        if (Directory.Exists(assetDir))
            iconTheme.AddSearchPath(assetDir);

        // 2. Load the CSS Provider
        var provider = Gtk.CssProvider.New();

        // We look for the theme relative to the App's execution directory
        string themePath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "share", "themes", subfolder, "gtk-4.0", "gtk.css");

        if (System.IO.File.Exists(themePath))
        {
            provider.LoadFromPath(themePath);

            // Priority 'User' (800) is what beats the default Adwaita theme
            Gtk.StyleContext.AddProviderForDisplay(
                display,
                provider,
                Gtk.Constants.STYLE_PROVIDER_PRIORITY_USER
            );
            Console.WriteLine($"Successfully loaded theme from: {themePath}");
        }
        else
        {
            Console.WriteLine($"CRITICAL: Theme not found at {themePath}");
        }

        var provider1 = Gtk.CssProvider.New();

        // This CSS targets the specific Adwaita nodes that create the circular 'halo'
        string breezeFixCss = @"
        /* 1. Reset the Adwaita circular backgrounds */
        windowcontrols button {
            border-radius: 0;
            background-color: transparent;
            background-image: none;
            box-shadow: none;
            padding: 0;
            margin: 0;
            min-width: 42px; /* Breeze standard width */
            min-height: 32px;
        }

        /* 2. Allow Breeze icons to show through */
        windowcontrols button image {
            background: none;
            box-shadow: none;
            -gtk-icon-shadow: none;
            opacity: 1;
        }

        /* 3. Re-enable the Breeze Hover effect if it's missing */
        windowcontrols button:hover {
            background-color: rgba(255, 255, 255, 0.1);
        }

        windowcontrols button.close:hover {
            background-color: #e81123;
        }
    ";

        provider1.LoadFromData(breezeFixCss, breezeFixCss.Length);
        // Use STYLE_PROVIDER_PRIORITY_APPLICATION (600) so the THEME (800) can still provide icons
        Gtk.StyleContext.AddProviderForDisplay(display, provider1, 600);

        // 3. Force Font Settings
        var settings = Gtk.Settings.GetForDisplay(display);
        if (settings != null)
        {
            settings.GtkFontName = "Segoe UI 10";
        }
    }
#endif

    // Create a standard Gtk.Window
    var window = Gtk.ApplicationWindow.New((Gtk.Application)sender);
    window.SetTitle("FFGUI Dotnet (Pure GTK4)");
    window.SetDefaultSize(400, 300);

    // Create a container
    var box = Gtk.Box.New(Gtk.Orientation.Vertical, 12);
    box.MarginTop = 20;
    box.MarginBottom = 20;
    box.MarginStart = 20;
    box.MarginEnd = 20;

    var label = Gtk.Label.New("This is a pure GTK4 Window");
    box.Append(label);

    var button = Gtk.Button.NewWithLabel("Click Me");
    button.OnClicked += (s, args) => label.SetText("Standard GTK Button Clicked!");
    box.Append(button);

    // This works perfectly for Gtk.Window / Gtk.ApplicationWindow
    window.SetChild(box);

    window.Show();
};

return app.Run(null);