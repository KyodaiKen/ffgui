using Gtk;
using System;

namespace FFGui.UI;

public class ProgressWindow : Window
{
    private ProgressBar _progressBar;
    private Label _statusLabel;
    private Button _btnCancel;
    public event EventHandler? OnCancelRequested;

    public ProgressWindow(Window? parent = null)
    {
        Title = "Analyzing Media...";
        SetDefaultSize(400, 150);
        Modal = true;
        Resizable = false;

        if (parent != null) SetTransientFor(parent);

        var vbox = new Box { Spacing = 12, MarginTop = 20, MarginBottom = 20, MarginStart = 20, MarginEnd = 20 };
        vbox.SetOrientation(Orientation.Vertical);
        SetChild(vbox);

        _statusLabel = new Label { Label_ = "Initializing...", Halign = Align.Start, Ellipsize = Pango.EllipsizeMode.End };
        vbox.Append(_statusLabel);

        _progressBar = new ProgressBar { ShowText = true };
        vbox.Append(_progressBar);

        _btnCancel = new Button { Label = "Cancel", Halign = Align.Center };
        _btnCancel.AddCssClass("destructive-action");
        _btnCancel.OnClicked += (s, e) => OnCancelRequested?.Invoke(this, EventArgs.Empty);

        vbox.Append(_btnCancel);
    }

    public void UpdateStatus(string text, double fraction)
    {
        _statusLabel.Label_ = text;
        _progressBar.Fraction = fraction;
    }
}