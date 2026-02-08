namespace FFGui.UI;

using Gtk;
using Gdk;
using System;
using System.IO;
using System.Reflection;
using FFGui.Core;

public class AboutWindow : Window
{
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

        string iconPath = Path.Combine(app.WorkingDir, "de.kyo.ffgui.svg");

        // --- Use Gtk.Picture for the Icon ---
        if (File.Exists(iconPath))
        {
            try
            {
                var texture = Texture.NewFromFilename(iconPath);

                // Gtk.Picture is designed to scale content
                var picture = new Picture();
                picture.SetPaintable(texture);

                // Force the size
                picture.SetSizeRequest(128, 128);

                // Ensure it scales correctly within that size (Contain = keep aspect ratio)
                picture.ContentFit = ContentFit.Contain;

                headerBox.Append(picture);
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Failed to load icon: {ex.Message}");
                // Fallback
                var fallback = Image.NewFromIconName("application-x-executable");
                fallback.PixelSize = 128;
                headerBox.Append(fallback);
            }
        }
        else
        {
            // Fallback if file missing
            var fallback = Image.NewFromIconName("de.kyo.ffgui");
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
            list.Append(rowBox);
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