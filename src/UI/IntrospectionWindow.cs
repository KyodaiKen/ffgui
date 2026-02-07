namespace FFGui.UI;

using Gtk;

public class IntrospectionWindow : Window
{
    private Label _label;
    private Label _label_p;
    private ProgressBar _progressBar;
    private Button _abortBtn;

    public IntrospectionWindow()
    {
        SetTitle("FFmpeg Introspection");
        SetDefaultSize(500, 128);
        SetSizeRequest(320, 128);
        SetResizable(false);
        SetModal(true);
        SetHideOnClose(true);

        var box = Box.New(Orientation.Vertical, 12);
        box.MarginTop = box.MarginBottom = box.MarginStart = box.MarginEnd = 24;

        var label = Label.New("Getting to know your FFMPEG installation");
        label.AddCssClass("introspection-label");

        _label = Label.New("Initializing...");
        _label.SetHalign(Align.Start);

        _progressBar = ProgressBar.New();
        _progressBar.SetFraction(0.0);

        _label_p = Label.New("");
        _label_p.SetHalign(Align.Center);

        _abortBtn = new Button { Label = "Abort & Quit" };
        _abortBtn.AddCssClass("destructive-action"); // Optional: makes it look like a "stop" button in some themes

        // Center the button
        _abortBtn.Halign = Gtk.Align.Center;
        _abortBtn.MarginTop = 12;
        _abortBtn.MarginBottom = 12;

        _abortBtn.OnClicked += (s, e) =>
        {
            this.Close();
        };

        box.Append(label);
        box.Append(_label);
        box.Append(_progressBar);
        box.Append(_label_p);
        box.Append(_abortBtn);

        SetChild(box);
    }

    public void UpdateProgress(string text, double fraction)
    {
        _label.SetText(text);
        _label_p.SetText($"{fraction * 100:0}%");
        _progressBar.SetFraction(fraction);
    }
}