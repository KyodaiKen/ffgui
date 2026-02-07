namespace FFGui.UI;

using Gtk;
using FFGui.Models;

public static partial class JobEditorUiFactory
{
    public static Box BuildStreamSetupBox(Job job, ref Dictionary<string, object> widgets)
    {

        var notebook = new Notebook()
        {
            Hexpand = true,
            Vexpand = true,
        };

        // Create pages
        (string Id, string Label, Dictionary<string, object> Widgets)[] pages = [
            ("pgStreamEncoder",     "Encoder",     null!),
            ("pgStreamFilters",     "Filters",     null!),
            ("pgStreamTrim",        "Trimming",    null!),
            ("pgStreamMetadata",    "Metadata",    null!),
            ("pgStreamParameters",  "Parameters",  null!),
        ];

        // Add page to notebook
        for (int i = 0; i < pages.Length; i++)
        {
            var currentPage = pages[i];
            int currentIndex = i;
            notebook.AppendPage(
                BuildJobUI(currentPage.Id, job, out pages[currentIndex].Widgets),
                new Label() { Label_ = currentPage.Label }
            );
        }

        widgets.Add("Pages", pages);
        widgets.Add("Notebook", notebook);

        var boxStreamSetup = BuildBox(0, 0, 0, 0, 0, Orientation.Horizontal);
        boxStreamSetup.Vexpand = true;
        boxStreamSetup.Valign = Align.Fill;
        boxStreamSetup.Hexpand = false;
        boxStreamSetup.Halign = Align.End;
        boxStreamSetup.Append(notebook);
        return boxStreamSetup;
    }
}
