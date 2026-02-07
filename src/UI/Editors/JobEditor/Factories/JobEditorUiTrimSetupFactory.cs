namespace FFGui.UI;

using Gtk;
using FFGui.Models;

public static partial class JobEditorUiFactory
{
    public static Box BuildTrimSetup(Job.Source.Stream.TrimSettings trimSettings, out Dictionary<string, object> widgets)
    {
        widgets = new();

        // 1. Create the container for the content
        var rootBox = BuildBox();

        // 2. Setup the Grid for Label/Entry pairs
        var grid = new Grid() { ColumnSpacing = 8, RowSpacing = 8 };
        rootBox.Append(grid);

        // Helper to add rows quickly and register widgets
        void AddTrimRow(string labelText, string propValue, string widgetKey, int row, Dictionary<string, object> targetDict)
        {
            var label = new Label() { Label_ = labelText, Xalign = 0 };
            var entry = new Entry() { Text_ = propValue, Hexpand = true };

            grid.Attach(label, 0, row, 1, 1);
            grid.Attach(entry, 1, row, 1, 1);

            targetDict.Add(widgetKey, entry);
        }

        AddTrimRow("Start Time:", trimSettings.Start, "entTrimStart", 0, widgets);
        AddTrimRow("Duration / Length:", trimSettings.Length, "entTrimLength", 1, widgets);
        AddTrimRow("End Time:", trimSettings.End, "entTrimEnd", 2, widgets);

        // 3. Optional: Add an info label about format
        var lblInfo = new Label()
        {
            Label_ = "<i>Use formats: HH:MM:SS, HH:MM:SS.mms, or total seconds.</i>",
            UseMarkup = true,
            Xalign = 0,
            MarginTop = 8
        };
        lblInfo.AddCssClass("dim-label"); // Standard Adwaita style for secondary text
        rootBox.Append(lblInfo);

        return rootBox;
    }
}
