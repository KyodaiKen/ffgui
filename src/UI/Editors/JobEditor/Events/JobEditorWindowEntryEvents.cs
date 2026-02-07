namespace FFGui.UI;

using Gtk;

public partial class JobEditorWindow
{
    private void _onEntryTextChanged(object? sender, EventArgs e, string pageId, string entryName)
    {
        if (_isUpdatingUi || sender is not Entry ent || _job == null)
            return;
#if VERBOSE
        Console.WriteLine($"Entry text change event triggered for {pageId}.{entryName}");
#endif
        switch (pageId)
        {
            case "main":
                switch (entryName)
                {
                    case "entJobName":
                        _job.Name = ent.GetText();
                        break;

                    case "entOutputFileName":
                        _job.OutputFileName = ent.GetText();
                        break;

                    case "entOutputDir":
                        _job.OutputDirectory = ent.GetText();
                        break;
                }
                break;
        }
    }
}
