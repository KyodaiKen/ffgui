namespace FFGui.UI;

using Gtk;
using Gdk;
using System;
using System.IO;
using System.Reflection;
using FFGui.Core;
using GLib;

public class AboutWindow : Window
{
    private const string iconData =
    """
        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    
    """;
    public AboutWindow(FFGuiApp app, Window parent)
    {
        // 1. Configure Window to be Modal and Blocking
        Title = "About FFGui";
        TransientFor = parent; // Keeps it on top of the parent
        Modal = true;          // Blocks interaction with the parent
        Resizable = false;
        SetDefaultSize(500, 450);

        // Main Layout
        var mainBox = new Box
        {
            Spacing = 16,
            MarginTop = 24,
            MarginBottom = 24,
            MarginStart = 24,
            MarginEnd = 24
        };
        mainBox.SetOrientation(Orientation.Vertical);
        SetChild(mainBox);

        // --- Header Section (Icon + Title + Version) ---
        var headerBox = new Box { Spacing = 8, Halign = Align.Center };
        headerBox.SetOrientation(Orientation.Vertical);


        // --- Load Embedded Icon ---
        try
        {
            byte[] bytes = Convert.FromBase64String(iconData);

            // Use PixbufLoader to decode the PNG bytes from memory
            var loader = new GdkPixbuf.PixbufLoader();
            loader.Write(bytes);
            loader.Close();

            var pixbuf = loader.GetPixbuf();
            if (pixbuf != null)
            {
                var texture = Texture.NewForPixbuf(pixbuf);
                var picture = new Picture
                {
                    Paintable = texture,
                    ContentFit = ContentFit.Contain,
                    CanShrink = false
                };
                picture.SetSizeRequest(128, 128);
                headerBox.Append(picture);
            }
        }
        catch (Exception ex)
        {
            Console.WriteLine($"[FFGui] Failed to load embedded icon: {ex.Message}");
            var fallback = Image.NewFromIconName("image-missing");
            fallback.PixelSize = 128;
            headerBox.Append(fallback);
        }

        // App Name
        var lblName = new Label { Label_ = "<span size='x-large' weight='bold'>FFGui</span>", UseMarkup = true };
        headerBox.Append(lblName);

        // Version Info
        var version = Assembly.GetExecutingAssembly().GetName().Version?.ToString() ?? "Unknown";
        var lblVersion = new Label { Label_ = $"Version {version}" };
        lblVersion.AddCssClass("dim-label");
        headerBox.Append(lblVersion);

        mainBox.Append(headerBox);

        // --- Paths List Section ---
        var frame = new Frame { Label = "Environment Configuration" };
        frame.Vexpand = true;

        var scroll = new ScrolledWindow { Vexpand = true, MinContentHeight = 200, HscrollbarPolicy = PolicyType.Never };
        var list = new ListBox { SelectionMode = SelectionMode.None, CanFocus = false };
        list.AddCssClass("rich-list"); // Native GTK styling for nice lists

        // Helper to add rows
        void AddRow(string title, string value)
        {
            var rowBox = new Box { Spacing = 2, MarginTop = 8, MarginBottom = 8, MarginStart = 12, MarginEnd = 12 };
            rowBox.SetOrientation(Orientation.Vertical);

            var lblTitle = new Label { Label_ = title, Xalign = 0 };
            lblTitle.AddCssClass("heading"); // Makes it slightly bold

            var lblValue = new Label
            {
                Label_ = value,
                Xalign = 0,
                Wrap = true,
                Selectable = true,
                WrapMode = Pango.WrapMode.WordChar
            };
            lblValue.AddCssClass("caption"); // Smaller text

            rowBox.Append(lblTitle);
            rowBox.Append(lblValue);

            var row = new ListBoxRow
            {
                Child = rowBox,
                Activatable = false,
                Selectable = false,
                CanFocus = false
            };
            list.Append(row);
        }

        // Add Data from App
        AddRow("Working Directory", app.WorkingDir);
        AddRow("FFmpeg Binary", app.FFMpegPath);
        AddRow("FFprobe Binary", app.FFProbePath);
        AddRow("FFplay Binary", app.FFPlayPath);
        AddRow("Cache File", app.FFMpegCachePath);

        // Handle Template Paths array
        string tplPaths = app.TemplatePaths != null
            ? string.Join("\n", app.TemplatePaths)
            : "None";
        AddRow("Template Directories", tplPaths);

        scroll.SetChild(list);
        frame.SetChild(scroll);
        mainBox.Append(frame);

        // --- Footer (Close Button) ---
        var btnClose = new Button { Label = "Close", Halign = Align.End };
        btnClose.AddCssClass("suggested-action");
        btnClose.OnClicked += (s, e) => this.Close();

        mainBox.Append(btnClose);
    }
}