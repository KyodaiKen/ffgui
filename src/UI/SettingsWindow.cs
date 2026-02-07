namespace FFGui.UI;

using Gtk;
using Gio;
using Gdk;
using GLib;
using HarfBuzz;

using FFGui.Core;
using FFGui.Models;

public class SettingsWindow : Window
{
    private FFGuiApp _app;

    private Entry _entryFFmPath;
    private string _initialFFmpegPath;
    private CheckButton _chkYamlBind;
    private Button _btnApply;
    private Button _btnCancel;

    public SettingsWindow(Gtk.Application app, Window parentWindow)
    {
        // Setup context
        _app = (FFGuiApp)app;
        Application = app;

        // Setup window
        SetTitle("Preferences");
        SetResizable(false);
        SetDefaultSize(500, 128);

        // Make window modal
        SetTransientFor(parentWindow);
        SetModal(true);

        //Grid
        var grid = new Grid()
        {
            Vexpand = true,
            Hexpand = true,
            MarginBottom = 20,
            MarginEnd = 20,
            MarginStart = 20,
            MarginTop = 20,
            ColumnSpacing = 20,
            RowSpacing = 8
        };
        SetChild(grid);

        //FFMPEG Path
        var label = new Label() { Label_ = "FFMPEG Binaries Path" };
        grid.Attach(label, 0, 0, 1, 1);
        _entryFFmPath = new Entry() { Hexpand = true, Text_ = _app.Settings.FFMpegPath };
        grid.Attach(_entryFFmPath, 1, 0, 1, 1);

        //Yaml auto bind setting
        _chkYamlBind = new() { Label = "Write efficient Yaml (harder to read and edit)" };
        _chkYamlBind.SetActive(_app.Settings.AllowYamlAliases);
        grid.Attach(_chkYamlBind, 0, 2, 2, 1);

        //Buttons
        var bb = new Box() { Spacing = 10, Halign = Align.End, MarginTop = 12 };
        bb.SetOrientation(Orientation.Horizontal);
        _btnApply = new() { Label = "Apply" };
        _btnApply.AddCssClass("suggested-action");
        bb.Append(_btnApply);
        _btnCancel = new() { Label = "Cancel", };
        _btnCancel.AddCssClass("destructive-action");
        bb.Append(_btnCancel);
        grid.Attach(bb, 0, 3, 2, 1);

        _initialFFmpegPath = _app.Settings.FFMpegPath;

        //Button events
        _btnApply.OnClicked += (s, e) =>
        {
            // Prevent double-triggering
            _btnApply.Sensitive = false;

            // Update settings
            _app.Settings.FFMpegPath = _entryFFmPath.Text_;
            _app.Settings.AllowYamlAliases = _chkYamlBind.GetActive();

            // Save to file
            var settingsPath = Path.Combine(_app.WorkingDir, "settings.yaml");
            _app.Settings.ToYaml(settingsPath);

            // Reinit and force retrospection if path has changed
            if (_app.Settings.FFMpegPath != _initialFFmpegPath)
            {
                _app.ResolveFFmpegBinaries();
                _ = _app.ReinitAsync(true);
            }

            //Update static state
            AppSettings.Load(_app.Settings);

            this.Close();
        };

        _btnCancel.OnClicked += (s, e) => this.Close();
    }
}
