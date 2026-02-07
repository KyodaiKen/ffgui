namespace FFGui.UI;

using Gtk;

public static partial class JobEditorUiFactory
{
    public static Box BuildMetadataSetup(Dictionary<string, object> metadata, out Dictionary<string, object> widgets)
    {
        widgets = new();

        var rootBox = BuildBox();

        var btnMSAddParam = Button.NewFromIconName("list-add-symbolic");
        btnMSAddParam.Halign = Align.End;
        rootBox.Append(btnMSAddParam);
        widgets.Add(nameof(btnMSAddParam), btnMSAddParam);

        var scroll = new ScrolledWindow()
        {
            Vexpand = true,
            Hexpand = true,
            HasFrame = true,
        };
        scroll.SetMinContentHeight(150);

        var lbMSMetadata = new ListBox() { SelectionMode = SelectionMode.None };
        lbMSMetadata.AddCssClass("boxed-list");
        scroll.SetChild(lbMSMetadata);
        widgets.Add(nameof(lbMSMetadata), lbMSMetadata);

        rootBox.Append(scroll);

        return rootBox;
    }

    public static ListBoxRow CreateMetadataRow(string key, string value, Action onRemove, Action onChanged)
    {
        var row = new ListBoxRow();
        var box = new Box { Spacing = 8, MarginStart = 6, MarginEnd = 6, MarginTop = 4, MarginBottom = 4 };

        box.SetOrientation(Orientation.Horizontal);
        var entKey = new Entry { Text_ = key, PlaceholderText = "Key" };
        var entValue = new Entry { Text_ = value, PlaceholderText = "Value", Hexpand = true };
        var btnDel = Button.NewFromIconName("user-trash-symbolic");

        // Connect the events to the onChanged callback
        entKey.OnNotify += (s, e) => { if (e.Pspec.GetName() == "text") onChanged(); };
        entValue.OnNotify += (s, e) => { if (e.Pspec.GetName() == "text") onChanged(); };

        btnDel.OnClicked += (s, e) => onRemove();

        box.Append(entKey);
        box.Append(entValue);
        box.Append(btnDel);
        row.SetChild(box);

        return row;
    }
}
