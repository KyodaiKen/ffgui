namespace FFGui.UI;

using Gtk;

public static partial class JobEditorUiFactory
{
    public static Box BuildStreamParameterSetup(List<string> disposition, string language, string delay, Dictionary<string, object> streamParameters, out Dictionary<string, object> widgets)
    {
        widgets = new();

        // Root Container
        var rootBox = BuildBox();

        // Fixed Top Grid
        var topGrid = new Grid() { ColumnSpacing = 8, RowSpacing = 8 };
        rootBox.Append(topGrid);

        // --- ROW 0: Language ---
        var lblLang = new Label() { Label_ = "Language:", Xalign = 0 };
        topGrid.Attach(lblLang, 0, 0, 1, 1);

        var langBox = new Box() { Spacing = 4 };
        var entLanguage = new Entry() { Text_ = language, Hexpand = true };
        langBox.Append(entLanguage);
        widgets.Add(nameof(entLanguage), entLanguage);

        var btnPSPickLanguage = Button.NewFromIconName("system-search-symbolic");
        btnPSPickLanguage.TooltipText = "Search Language";
        langBox.Append(btnPSPickLanguage);
        widgets.Add(nameof(btnPSPickLanguage), btnPSPickLanguage);
        topGrid.Attach(langBox, 1, 0, 1, 1);

        // --- ROW 1: Delay ---
        var lblDelay = new Label() { Label_ = "Delay:", Xalign = 0 };
        topGrid.Attach(lblDelay, 0, 1, 1, 1);

        var entDelay = new Entry() { Text_ = delay, Hexpand = true };
        topGrid.Attach(entDelay, 1, 1, 1, 1);
        widgets.Add(nameof(entDelay), entDelay);

        // --- ROW 2: Disposition (FlowBox) ---
        var lblDisp = new Label() { Label_ = "Disposition:", Xalign = 0, Valign = Align.Start };
        topGrid.Attach(lblDisp, 0, 2, 1, 1);

        var flowBoxContainer = BuildBox(2, 0, 0, 0, 0, Orientation.Horizontal);
        flowBoxContainer.Vexpand = true;

        // Create the FlowBox
        var fbDisposition = new FlowBox()
        {
            SelectionMode = SelectionMode.None,
            Hexpand = true,
            Halign = Align.Fill,
            Valign = Align.Start,
            ColumnSpacing = 2,
            RowSpacing = 2,
            MaxChildrenPerLine = 2,
            MinChildrenPerLine = 1,
            Homogeneous = true,
        };
        fbDisposition.AddCssClass("fb-dispositions");
        widgets.Add(nameof(fbDisposition), fbDisposition);

        // Wrap it in a ScrolledWindow
        var scroll = new ScrolledWindow()
        {
            Child = fbDisposition,
            Hexpand = true,
            Vexpand = true,
            HasFrame = true,
            MinContentHeight = 120,
            PropagateNaturalWidth = true
        };
        scroll.SetPolicy(PolicyType.Never, PolicyType.Automatic);
        flowBoxContainer.Append(scroll);

        // Fill the FlowBox with pills
        foreach (var dispTag in disposition)
            fbDisposition.Append(CreatePill(dispTag, widgets, () => { }));

        // Add a button to add new disposition tags
        var btnPSAddDisposition = Button.NewFromIconName("list-add-symbolic");
        btnPSAddDisposition.MarginStart = 4;
        btnPSAddDisposition.Valign = Align.Start;
        btnPSAddDisposition.TooltipText = "Add Disposition Tag";
        flowBoxContainer.Append(btnPSAddDisposition);
        widgets.Add(nameof(btnPSAddDisposition), btnPSAddDisposition);

        topGrid.Attach(flowBoxContainer, 1, 2, 1, 1);

        return rootBox;
    }
}
