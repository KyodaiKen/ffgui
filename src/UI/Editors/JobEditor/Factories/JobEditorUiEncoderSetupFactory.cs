namespace FFGui.UI;

using Gtk;
using FFGui.Models;

public static partial class JobEditorUiFactory
{
    public static Widget BuildEncoderSetup(EncoderSettings encoderSettings, out Dictionary<string, object> widgets)
    {
        widgets = new();

        // The root container (Vertical Box)
        var rootBox = BuildBox();

        // The Fixed Grid for the top controls
        var topGrid = new Grid() { ColumnSpacing = 8, RowSpacing = 8 };
        rootBox.Append(topGrid);

        // --- ROW 0: Encoder Selection ---
        var lblEncoder = new Label() { Label_ = "Encoder:", Xalign = 0 };
        topGrid.Attach(lblEncoder, 0, 0, 1, 1);

        var encoderBox = new Box() { Spacing = 4 };
        var entEncoder = new Entry() { Text_ = encoderSettings.Encoder, CanFocus = false, Editable = false, Hexpand = true };
        encoderBox.Append(entEncoder);
        widgets.Add(nameof(entEncoder), entEncoder);

        var btnESPickEncoder = Button.NewFromIconName("system-search-symbolic");
        btnESPickEncoder.TooltipText = "Select Encoder";
        encoderBox.Append(btnESPickEncoder);
        widgets.Add(nameof(btnESPickEncoder), btnESPickEncoder);

        var btnESLoadTemplate = Button.NewFromIconName("document-open-symbolic");
        btnESLoadTemplate.TooltipText = "Load Transcoding Template";
        encoderBox.Append(btnESLoadTemplate);
        widgets.Add(nameof(btnESLoadTemplate), btnESLoadTemplate);

        topGrid.Attach(encoderBox, 1, 0, 1, 1);

        // --- ROW 1: Header for Options ---
        var lblOptions = new Label() { Label_ = "<b>Encoder Options</b>", UseMarkup = true, Xalign = 0 };
        topGrid.Attach(lblOptions, 0, 1, 1, 1);

        var btnESAddParam = Button.NewFromIconName("list-add-symbolic");
        btnESAddParam.Halign = Align.End;
        topGrid.Attach(btnESAddParam, 1, 1, 1, 1);
        widgets.Add(nameof(btnESAddParam), btnESAddParam);

        // The ScrolledWindow (Only for the ListBox)
        var scroll = new ScrolledWindow()
        {
            Vexpand = true,
            Hexpand = true,
            HasFrame = true,
        };
        scroll.SetMinContentHeight(150);

        var lbESEncoderParams = new ListBox() { SelectionMode = SelectionMode.None };
        lbESEncoderParams.AddCssClass("boxed-list");
        scroll.SetChild(lbESEncoderParams);
        widgets.Add(nameof(lbESEncoderParams), lbESEncoderParams);

        rootBox.Append(scroll);

        return rootBox;
    }
}
