namespace FFGui.UI;

using Gtk;

public static partial class JobEditorUiFactory
{
    public static Box BuildContainerSetupBox(string multiplexer, Dictionary<string, object> muxerParameters, out Dictionary<string, object> widgets)
    {
        widgets = [];
        var colLeft = BuildBox(8, 0, 0, 0, 0, Orientation.Vertical);

        // hbox: Format Selection
        var boxFormatRow = new Box() { Spacing = 6 };
        boxFormatRow.Append(new Label() { Label_ = "Container Format:", Xalign = 0 });

        var entCSContainerFormat = new Entry()
        {
            Text_ = multiplexer ?? "",
            Editable = false,
            CanFocus = false,
            Hexpand = true
        };
        widgets.Add(nameof(entCSContainerFormat), entCSContainerFormat);
        boxFormatRow.Append(entCSContainerFormat);

        var btnCSSelectContainer = Button.NewFromIconName("system-search-symbolic");
        btnCSSelectContainer.TooltipText = "Select Container Format";
        widgets.Add(nameof(btnCSSelectContainer), btnCSSelectContainer);
        boxFormatRow.Append(btnCSSelectContainer);

        var btnCSLoadContainerTemplate = Button.NewFromIconName("document-open-symbolic");
        btnCSLoadContainerTemplate.TooltipText = "Load Container Template";
        widgets.Add(nameof(btnCSLoadContainerTemplate), btnCSLoadContainerTemplate);
        boxFormatRow.Append(btnCSLoadContainerTemplate);
        colLeft.Append(boxFormatRow);

        // Muxer Parameters List
        var boxMuxerHeader = new Box() { Spacing = 4 };
        boxMuxerHeader.Append(new Label() { Label_ = "<b>Format Parameters</b>", UseMarkup = true, Xalign = 0, Hexpand = true });
        var btnCSAddMuxParam = Button.NewFromIconName("list-add-symbolic");
        widgets.Add(nameof(btnCSAddMuxParam), btnCSAddMuxParam);
        boxMuxerHeader.Append(btnCSAddMuxParam);
        colLeft.Append(boxMuxerHeader);

        var scrollMuxParams = new ScrolledWindow() { Vexpand = true, HasFrame = true };
        scrollMuxParams.SetMinContentHeight(150);
        var lbCSMuxerParams = new ListBox() { SelectionMode = SelectionMode.None };
        lbCSMuxerParams.AddCssClass("boxed-list");
        scrollMuxParams.SetChild(lbCSMuxerParams);
        widgets.Add(nameof(lbCSMuxerParams), lbCSMuxerParams);
        colLeft.Append(scrollMuxParams);

        return colLeft;
    }
}
