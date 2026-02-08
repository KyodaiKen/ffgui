namespace FFGui.UI;

using Gtk;
using HarfBuzz;

public partial class JobEditorWindow
{
    private void _registerEvents(string pageId, Dictionary<string, object> widgets)
    {
        foreach (var widget in widgets)
        {
            switch (widget.Value)
            {
                case Button btn:
                    btn.OnClicked += (sender, args) => _onPageButtonClicked(pageId, widget.Key);
                    break;
                case CheckButton cb:
                    cb.OnToggled += (s, e) => _onToggleChanged(pageId, widget.Key, cb.Active);
                    break;
                case DropDown dd:
                    // We watch for the "selected" property notification
                    dd.OnNotify += (s, e) =>
                    {
                        if (e.Pspec.GetName() == "selected")
                        {
                            // Selected returns the uint index of the chosen item
                            _onDropDownChanged(pageId, widget.Key, (int)dd.Selected);
                        }
                    };
                    break;
                case ListBox lb:
                    lb.OnSelectedRowsChanged += (s, e) =>
                    {
                        var selectedRow = lb.GetSelectedRow();
                        int index = selectedRow?.GetIndex() ?? -1;
                        _onListSelectionChanged(pageId, widget.Key, index);
                    };

                    //Special cases such as drop targets
                    switch (widget.Key)
                    {
                        case "lstSourceFiles":
                            // Setup drop target for our Source list box
                            var dropTarget = Gtk.DropTarget.New(Gdk.FileList.GetGType(), Gdk.DragAction.Copy);
                            dropTarget.OnDrop += (sender, args) => _onSourceListFilesDrop(sender, args, lb);
                            lb.AddController(dropTarget);
                            break;
                    }
                    break;
                case (string Id, string Label, Dictionary<string, object> Widgets)[] subPages:
                    foreach (var subPage in subPages)
                    {
                        _registerEvents(subPage.Id, subPage.Widgets);
                    }
                    break;
            }
        }
    }

    // --- Helpers ---
    private ListBox? _getSourceListBox()
    {
        var page = _pages.FirstOrDefault(p => p.Id == "pgSources");
        if (page.Widgets != null && page.Widgets.TryGetValue("lstSourceFiles", out var lbObj))
            return lbObj as ListBox;
        return null;
    }

    private ListBox? _getStreamListBox()
    {
        // Locate the ListBox inside the pgStreams structure
        var page = _pages.FirstOrDefault(p => p.Id == "pgStreams");
        if (page.Widgets != null && page.Widgets.TryGetValue("lstStreams", out var lbObj))
            return lbObj as ListBox;
        return null;
    }

    private T? _getWidgetByPageAndPath<T>(string parentPageId, string subPageId, string widgetName) where T : Widget
    {
        var parentPage = _pages.FirstOrDefault(p => p.Id == parentPageId);
        if (parentPage.Widgets is not null)
        {

            if (parentPage.Widgets.TryGetValue("Pages", out var pagesObj))
            {
                var nestedPages = ((string Id, string Label, Dictionary<string, object> Widgets)[])pagesObj;
                var subPage = nestedPages.FirstOrDefault(sp => sp.Id == subPageId);

                if (subPage.Widgets != null && subPage.Widgets.TryGetValue(widgetName, out var widget))
                {
                    return widget as T;
                }
            }

            // Fallback: If no sub-page was found, check if the widget exists directly on the parent
            if (parentPage.Widgets.TryGetValue(widgetName, out var directWidget))
            {
                return directWidget as T;
            }
        }

        // Fallback: Look in _widgets instead
        if (_widgets.TryGetValue(widgetName, out var w))
            return w as T;

        return null;
    }

    private T? _getWidgetByPageAndPath<T>(string parentPageId, string widgetName) where T : Widget
    {
        return _getWidgetByPageAndPath<T>(parentPageId, "", widgetName);
    }
}