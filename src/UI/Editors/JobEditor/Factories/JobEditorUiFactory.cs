namespace FFGui.UI;

using Gtk;
using FFGui.Models;

public static partial class JobEditorUiFactory
{
    public static Widget BuildJobUI(string pageId, Job job, out Dictionary<string, object> widgets)
    {
        widgets = new();

        switch (pageId)
        {
            case "pgSources":
                var grid = new Grid()
                {
                    Name = pageId,
                    RowSpacing = 8,
                    ColumnSpacing = 8,
                    Vexpand = true,
                    MarginBottom = 8,
                    MarginEnd = 8,
                    MarginStart = 8,
                    MarginTop = 8
                };
                grid.SetOrientation(Orientation.Vertical);

                var lstSourceFiles = new ListBox() { Hexpand = true };
                lstSourceFiles.SetSelectionMode(SelectionMode.Single);
                lstSourceFiles.SetActivateOnSingleClick(false);
                widgets.Add(nameof(lstSourceFiles), lstSourceFiles);

                var scrollSourceList = new ScrolledWindow();
                scrollSourceList.SetChild(lstSourceFiles);
                scrollSourceList.SetMinContentHeight(120);
                scrollSourceList.SetMaxContentHeight(120);
                scrollSourceList.SetPropagateNaturalHeight(true);
                widgets.Add(nameof(scrollSourceList), scrollSourceList);

                grid.Attach(scrollSourceList, 0, 0, 1, 1);

                var boxLstSourcesButtons = new Box() { Spacing = 8, Vexpand = true, Valign = Align.Fill };
                boxLstSourcesButtons.SetOrientation(Orientation.Vertical);

                // Define buttons
                (string name, string[] css, string label)[] btnListSrcs = [
                    ("btnAdd"   , []                        , "Add File(s)"),
                    ("btnRm"    , ["destructive-action"]    , "Remove Selected"),
                    ("btnUp"    , []                        , "Move Up"),
                    ("btnDwn"   , []                        , "Move Down"),
                    ("btnClr"   , []                        , "Clear List")
                ];

                // Create buttons
                foreach ((string name, string[] css, string label) btnTpl in btnListSrcs)
                {
                    widgets.Add(btnTpl.name, new Button() { Label = btnTpl.label, CssClasses = btnTpl.css });
                    if (widgets[btnTpl.name] is Button btn) boxLstSourcesButtons.Append(btn);
                }

                grid.Attach(boxLstSourcesButtons, 1, 0, 1, 1);
                return grid;

            case "pgStreams":
                var outerBox = BuildBox(8, 8, 8, 8, 8, Orientation.Horizontal);
                outerBox.Vexpand = true;
                outerBox.Valign = Align.Fill;
                outerBox.Hexpand = true;
                outerBox.Halign = Align.Fill;

                var lstStreams = new ListBox() { Hexpand = true };
                lstStreams.SetSelectionMode(SelectionMode.Single);
                lstStreams.SetActivateOnSingleClick(true);
                widgets.Add(nameof(lstStreams), lstStreams);

                var scrollStreams = new ScrolledWindow();
                scrollStreams.SetChild(lstStreams);
                scrollStreams.SetMinContentHeight(120);
                scrollStreams.SetMaxContentHeight(120);
                scrollStreams.SetPropagateNaturalHeight(true);
                widgets.Add(nameof(scrollStreams), scrollStreams);

                outerBox.Append(scrollStreams);

                var boxStreamSetup = BuildStreamSetupBox(job, ref widgets);
                boxStreamSetup.SetSizeRequest(480, -1);
                widgets.Add(nameof(boxStreamSetup), boxStreamSetup);
                outerBox.Append(boxStreamSetup);

                return outerBox;
            case "pgContainer":
                // Using a Grid with ColumnHomogeneous ensures a perfect 50/50 split
                var gridContainerMain = new Grid()
                {
                    ColumnSpacing = 24,
                    RowSpacing = 8,
                    MarginBottom = 6,
                    MarginEnd = 6,
                    MarginStart = 6,
                    MarginTop = 6,
                    ColumnHomogeneous = true, // This is the magic line for 50/50
                    Vexpand = true,
                    Hexpand = true
                };

                // --- LEFT COLUMN: Multiplexer & Parameters ---
                var colLeft = BuildContainerSetupBox(job.Multiplexer, job.MuxerParameters, out widgets);

                // --- RIGHT COLUMN: Global Metadata ---
                var colRight = BuildBox(8, 0, 0, 0, 0, Orientation.Vertical);

                var boxMetadataHeader = new Box() { Spacing = 4 };
                boxMetadataHeader.Append(new Label() { Label_ = "<b>Global Metadata</b>", UseMarkup = true, Xalign = 0, Hexpand = true });
                var btnCSAddMetadata = Button.NewFromIconName("list-add-symbolic");
                widgets.Add(nameof(btnCSAddMetadata), btnCSAddMetadata);
                boxMetadataHeader.Append(btnCSAddMetadata);
                colRight.Append(boxMetadataHeader);

                var scrollMetadata = new ScrolledWindow() { Vexpand = true, HasFrame = true };
                scrollMetadata.SetMinContentHeight(150);
                var lbCSMetadata = new ListBox() { SelectionMode = SelectionMode.None };
                lbCSMetadata.AddCssClass("boxed-list");
                scrollMetadata.SetChild(lbCSMetadata);
                widgets.Add(nameof(lbCSMetadata), lbCSMetadata);
                colRight.Append(scrollMetadata);

                // Attach columns to the Grid
                gridContainerMain.Attach(colLeft, 0, 0, 1, 1);
                gridContainerMain.Attach(colRight, 1, 0, 1, 1);

                return gridContainerMain;
            // These are set up later with selected stream data, so they get empty data.
            case "pgStreamEncoder":
                return BuildEncoderSetup(new EncoderSettings(), out widgets);
            case "pgStreamFilters":
                return BuildFilterSetup(false, out widgets);
            case "pgStreamTrim":
                return BuildTrimSetup(new Job.Source.Stream.TrimSettings(), out widgets);
            case "pgStreamMetadata":
                return BuildMetadataSetup([], out widgets);
            case "pgStreamParameters":
                return BuildStreamParameterSetup([], "und", "", [], out widgets);
            default:
                throw new NotImplementedException($"No such page {pageId}");
        }
    }
    

    // Private tools
    private static Box BuildBox(int spacing = 8, int marginStart = 8, int marginEnd = 8, int marginTop = 8, int marginBottom = 8, Orientation orientation = Orientation.Vertical)
    {
        var rootBox = new Box()
        {
            Spacing = spacing,
            MarginStart = marginStart,
            MarginEnd = marginEnd,
            MarginTop = marginTop,
            MarginBottom = marginBottom
        };
        rootBox.SetOrientation(orientation);
        return rootBox;
    }
    public static ScrolledWindow BuildScrolledWindow(int spacing = 8, int minHeight = 120, int maxHeight = 120)
    {
        var box = new Box() { Spacing = spacing, Vexpand = true, Valign = Align.Fill, Hexpand = false, Halign = Align.End };

        var scroll = new ScrolledWindow();
        scroll.SetChild(box);
        scroll.SetMinContentHeight(minHeight);
        scroll.SetMaxContentHeight(maxHeight);
        scroll.SetPropagateNaturalHeight(true);

        return scroll;
    }

    public static Widget CreatePill(string text, Dictionary<string, object> widgets, Action onRemove)
    {
        var box = new Box() { Spacing = 0, Hexpand = false, Halign = Align.Start, Valign = Align.Start };
        box.AddCssClass("disposition-tag"); // Requires CSS for rounded corners

        var label = new Label() { Label_ = text };
        box.Append(label);

        var btnRemove = Button.NewFromIconName("user-trash-symbolic");
        btnRemove.AddCssClass("flat");
        btnRemove.Valign = Align.Center;
        btnRemove.Halign = Align.End;

        btnRemove.OnClicked += (s, e) => onRemove();

        box.Append(btnRemove);

        return box;
    }
}
