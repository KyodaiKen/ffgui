namespace FFGui.UI;

using Gtk;
using FFGui.Models;

public static partial class JobEditorUiFactory
{
    public class FilterRow : ListBoxRow
    {
        // The managed reference to our data model
        public EncoderSettings.FilterSettings Settings { get; }

        public FilterRow(EncoderSettings.FilterSettings settings, Widget child)
        {
            Settings = settings;
            SetChild(child);
        }
    }
    public static Widget BuildFilterSetup(bool filterComplex, out Dictionary<string, object> widgets)
    {
        widgets = new();

        var rootBox = BuildBox();

        // --- Top Controls: Filter Mode ---
        var topGrid = new Grid() { ColumnSpacing = 8, RowSpacing = 12 };
        rootBox.Append(topGrid);

        var lblMode = new Label() { Label_ = "Filter Mode:", Xalign = 0 };
        topGrid.Attach(lblMode, 0, 0, 1, 1);

        // DropDown for Simple/Complex
        var ddFilterMode = DropDown.NewFromStrings(["Simple", "Complex"]);
        ddFilterMode.Hexpand = true;
        ddFilterMode.Selected = filterComplex == true ? 1u : 0u;
        topGrid.Attach(ddFilterMode, 1, 0, 1, 1);
        widgets.Add("ddFilterMode", ddFilterMode);

        // --- The Stack (Dynamic Area) ---
        var modeStack = new Stack()
        {
            TransitionType = StackTransitionType.Crossfade,
            Vexpand = true
        };
        rootBox.Append(modeStack);
        widgets.Add("filterModeStack", modeStack);

        // --- SIMPLE MODE UI ---
        var simpleBox = BuildBox(8, 0, 0, 0, 0, Orientation.Vertical);

        var simpleHeader = BuildBox(4, 0, 0, 0, 0, Orientation.Horizontal);
        simpleHeader.Append(new Label() { Label_ = "<b>Filters</b>", UseMarkup = true, Xalign = 0, Hexpand = true });

        var btnFSLoadTemplate = Button.NewFromIconName("document-open-symbolic");
        btnFSLoadTemplate.TooltipText = "Load Filter Template";
        btnFSLoadTemplate.Halign = Align.End;
        simpleHeader.Append(btnFSLoadTemplate);
        widgets.Add(nameof(btnFSLoadTemplate), btnFSLoadTemplate);

        var btnFSAddFilter = Button.NewFromIconName("list-add-symbolic");
        btnFSAddFilter.Halign = Align.End;
        simpleHeader.Append(btnFSAddFilter);
        widgets.Add("btnFSAddFilter", btnFSAddFilter);
        simpleBox.Append(simpleHeader);

        var scrollSimple = new ScrolledWindow() { Vexpand = true, HasFrame = true };
        var lbFilters = new ListBox() { SelectionMode = SelectionMode.None };
        lbFilters.AddCssClass("boxed-list");
        scrollSimple.SetChild(lbFilters);
        simpleBox.Append(scrollSimple);
        widgets.Add("listSimpleFilters", lbFilters);

        // --- COMPLEX MODE UI ---
        var complexBox = new Box() { Spacing = 8 };
        complexBox.SetOrientation(Orientation.Vertical);

        var btnFSOpenGraph = new Button() { Label = "Open Filter Graph Editor", Hexpand = true };
        complexBox.Append(btnFSOpenGraph);
        widgets.Add("btnFSOpenGraph", btnFSOpenGraph);

        var previewFrame = new Frame() { Vexpand = true, Hexpand = true };
        // Using a Picture for the graph preview
        var imgGraph = new Picture()
        {
            CanShrink = true,
            ContentFit = ContentFit.Contain
        };
        // Standard GTK styling for a black background box
        imgGraph.AddCssClass("graph-preview-area");
        previewFrame.SetChild(imgGraph);
        complexBox.Append(previewFrame);
        widgets.Add("imgGraphPreview", imgGraph);

        // Add children to stack
        modeStack.AddNamed(simpleBox, "Simple");
        modeStack.AddNamed(complexBox, "Complex");

        // Logic to switch stack based on DropDown
        ddFilterMode.OnNotify += (s, e) =>
        {
            if (e.Pspec.GetName() == "selected")
            {
                modeStack.VisibleChildName = ddFilterMode.Selected == 0 ? "Simple" : "Complex";
            }
        };

        return rootBox;
    }
    public static FilterRow CreateFilterRow(EncoderSettings.FilterSettings filter, Action<ListBoxRow> onRemove, Action onEdit)
    {
        var box = new Box { Spacing = 12, MarginStart = 8, MarginEnd = 8, MarginTop = 6, MarginBottom = 6 };
        var row = new FilterRow(filter, box);

        var labelBox = new Box { Hexpand = true };
        labelBox.SetOrientation(Orientation.Vertical);
        labelBox.Append(new Label { Label_ = $"<b>{filter.FilterName}</b>", UseMarkup = true, Xalign = 0 });

        // Format: key: value, key: value...
        string paramSummary = string.Join(", ", filter.Parameters.Select(p => $"{p.Key}: {p.Value}"));
        var lblParams = new Label
        {
            Label_ = paramSummary,
            Xalign = 0,
            Opacity = 0.6,
            Ellipsize = Pango.EllipsizeMode.End,
            MaxWidthChars = 50 // Ellipse if too long
        };
        lblParams.AddCssClass("caption");
        labelBox.Append(lblParams);
        box.Append(labelBox);

        // Edit Button
        var btnEdit = Button.NewFromIconName("document-edit-symbolic");
        btnEdit.AddCssClass("flat");
        btnEdit.OnClicked += (s, e) => onEdit();
        box.Append(btnEdit);

        // Remove Button
        var btnRemove = Button.NewFromIconName("user-trash-symbolic");
        btnRemove.AddCssClass("flat");
        btnRemove.OnClicked += (s, e) => onRemove(row);
        box.Append(btnRemove);

        row.SetChild(box);
        return row;
    }
}
