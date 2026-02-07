namespace FFGui.UI;

public partial class JobEditorWindow
{
    private void _onToggleChanged(string page, string cb, bool active)
    {
#if VERBOSE
        Console.WriteLine($"{page}.{cb} changed to {active}");
#endif
        switch (page)
        {
            default:

                break;
        }
    }

    private void _onDropDownChanged(string page, string dropDownName, int selectedIndex)
    {
#if VERBOSE
        Console.WriteLine($"{page}.{dropDownName} selection changed to index: {selectedIndex}");
#endif
    }
}
