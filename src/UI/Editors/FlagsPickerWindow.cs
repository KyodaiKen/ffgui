namespace FFGui.UI;

using Gtk;
using FFGui.Models;
using System.Linq;

public class FlagsPickerWindow : Window
{
    private readonly Action<string> _onApply;
    private readonly Dictionary<string, CheckButton> _checks = new();

    public FlagsPickerWindow(string key, Dictionary<string, FFmpegOption> options, string current, Action<string> onApply)
    {
        _onApply = onApply;

        SetTitle($"Select {key} Flags");
        SetDefaultSize(350, 450);
        SetModal(true);

        var header = new HeaderBar();
        var btnApply = new Button { Label = "Apply" };
        btnApply.OnClicked += (s, e) => _apply();
        header.PackEnd(btnApply);
        SetTitlebar(header);

        var vbox = new Box { Spacing = 10, MarginStart = 12, MarginEnd = 12, MarginTop = 12, MarginBottom = 12 };
        vbox.SetOrientation(Orientation.Vertical);
        
        var list = new ListBox { SelectionMode = SelectionMode.None };
        list.AddCssClass("boxed-list");

        var currentFlags = current.Split('+', StringSplitOptions.RemoveEmptyEntries).Select(f => f.Trim()).ToList();

        foreach (var opt in options)
        {
            var row = new Box { Spacing = 10, MarginTop = 4, MarginBottom = 4 };
            var chk = new CheckButton { Label = opt.Key, Active = currentFlags.Contains(opt.Key) };
            _checks[opt.Key] = chk;

            row.Append(chk);
            if (!string.IsNullOrEmpty(opt.Value.Description))
            {
                var lbl = new Label { Label_ = opt.Value.Description, Xalign = 0, Opacity = 0.6, Ellipsize = Pango.EllipsizeMode.End, Hexpand = true };
                lbl.AddCssClass("caption");
                row.Append(lbl);
            }
            list.Append(row);
        }

        vbox.Append(new ScrolledWindow { Child = list, Vexpand = true });
        SetChild(vbox);
    }

    private void _apply()
    {
        var selected = _checks.Where(kv => kv.Value.Active).Select(kv => kv.Key);
        _onApply(string.Join("+", selected));
        this.Close();
    }
}