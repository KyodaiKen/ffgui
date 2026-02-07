namespace FFGui.UI;

using Gtk;
using FFGui.Models;
using System.Linq;

public class PickerWindow : Window
{
    private readonly FFmpegCache _cache;
    private readonly PickerType _type;
    private readonly Action<object> _onPicked;
    private readonly string _streamType;
    private readonly string? _parentKey;
    private readonly object? _contextData;

    private ListBox _listBox;
    private SearchEntry _searchEntry;
    private List<PickerItem> _allItems = new();

    private record PickerItem(string Key, string Description, object RawData, bool IsGlobal = false);
    public record PickerResult(string Key, object Data);

    private class PickerRow : ListBoxRow
    {
        public object Data { get; init; } = null!;
    }

    public PickerWindow(
        FFmpegCache cache,
        PickerType type,
        Action<object> onPicked,
        string? parentKey = null,
        object? contextData = null,
        string streamType = "") // New optional parameter
    {
        _cache = cache;
        _type = type;
        _onPicked = onPicked;
        _parentKey = parentKey;
        _contextData = contextData;
        _streamType = streamType.ToLower();

        SetTitle($"Select {_type} {(_streamType != "" ? $"({_streamType})" : "")}");
        SetDefaultSize(400, 500);
        SetModal(true);

        var header = new HeaderBar();
        _searchEntry = new SearchEntry { PlaceholderText = "Search keys or descriptions..." };
        _searchEntry.OnChanged += (s, e) => _updateFilter();
        header.SetTitleWidget(_searchEntry);
        SetTitlebar(header);

        var scroller = new ScrolledWindow { Vexpand = true, PropagateNaturalHeight = true };
        _listBox = new ListBox();

        _listBox.OnRowActivated += (s, e) =>
        {
            if (e.Row is PickerRow row)
            {
                _onPicked(row.Data);
                this.Close();
            }
        };

        scroller.SetChild(_listBox);
        SetChild(scroller);

        _loadData();
        _updateFilter();

        GLib.Functions.IdleAdd(0, () =>
        {
            _searchEntry.GrabFocus();
            return false;
        });
    }

    private void _loadData()
    {
        _allItems.Clear();
        switch (_type)
        {
            case PickerType.Encoder:
                var encoders = _cache.Codecs.Where(x => x.Value.Flags.Encoder);

                // Filter by Stream Type
                if (_streamType == "video") encoders = encoders.Where(x => x.Value.Flags.Video);
                else if (_streamType == "audio") encoders = encoders.Where(x => x.Value.Flags.Audio);
                else if (_streamType == "subtitle") encoders = encoders.Where(x => x.Value.Flags.Subtitle);

                // Manually add the "copy" stream codec
                _allItems.Add(new PickerItem(
                    "copy",
                    "Stream copy (re-mux without re-encoding)",
                    new PickerResult("copy", null!) // No FFmpegCodec object exists for copy
                ));

                foreach (var (k, v) in encoders)
                    _allItems.Add(new PickerItem(k, v.Description, new PickerResult(k, v)));
                break;

            case PickerType.Filter:
                var filters = _cache.Filters.AsEnumerable();

                // Filters use Inputs/Outputs to determine type usually, but we check Context
                if (_streamType == "video") filters = filters.Where(x => x.Value.Parameters.Values.Any(p => p.Context.Video));
                else if (_streamType == "audio") filters = filters.Where(x => x.Value.Parameters.Values.Any(p => p.Context.Audio));

                foreach (var (k, v) in filters)
                    _allItems.Add(new PickerItem(k, v.Description, new PickerResult(k, v)));
                break;

            case PickerType.Muxer:
                foreach (var (k, v) in _cache.Formats.Where(x => x.Value.IsMuxer))
                    _allItems.Add(new PickerItem(k, v.Description, new PickerResult(k, v)));
                break;

            case PickerType.Parameter:
                _loadParametersFromContext();
                break;

            case PickerType.Option:
                if (_contextData is FFmpegParameter p && p.Options is not null)
                {
                    foreach (var (k, v) in p.Options)
                    {
                        string desc = string.IsNullOrEmpty(v.Description)
                            ? $"Value: {_getOptionValueString(v.Value)}"
                            : v.Description;
                        _allItems.Add(new PickerItem(k, desc, new PickerResult(k, v)));
                    }
                }
                break;

            case PickerType.PixelFormat:
                // Pixel formats are only relevant for Video
                if (_streamType == "" || _streamType == "video")
                {
                    foreach (var (k, v) in _cache.PixelFormats)
                        _allItems.Add(new PickerItem(k, "", new PickerResult(k, v)));
                }
                break;
            case PickerType.Language:
                _loadLanguages();
                break;
        }
    }

    private void _loadParametersFromContext()
    {
        _allItems.Clear();

        // 1. --- Load context-specific parameters ---
        if (_contextData is FFmpegFilter flt)
        {
            foreach (var (k, v) in flt.Parameters)
                _allItems.Add(new PickerItem(k, v.Description ?? "", new PickerResult(k, v), IsGlobal: false));
        }
        else if (_contextData is FFmpegFormat f)
        {
            // For Formats (Muxers), we want to show ALL format parameters
            // regardless of whether the internal context.Video/Audio flags are false.
            foreach (var (k, v) in f.Parameters)
                _allItems.Add(new PickerItem(k, v.Description ?? "", new PickerResult(k, v), IsGlobal: false));
        }
        else if (_contextData is FFmpegCodec c)
        {
            foreach (var (k, v) in c.Parameters)
                _allItems.Add(new PickerItem(k, v.Description ?? "", new PickerResult(k, v), IsGlobal: false));
        }

        // 2. --- Load Global Parameters (Stream Specific) ---
        var globalsToAdd = new List<KeyValuePair<string, FFmpegParameter>>();

        // If we are looking at a Format, we usually only care about PerStream globals 
        // and the specific Format params we just added above.
        if (_contextData is not FFmpegFormat)
        {
            if (_streamType == "video") globalsToAdd.AddRange(_cache.Globals.Video);
            else if (_streamType == "audio") globalsToAdd.AddRange(_cache.Globals.Audio);
            else if (_streamType == "subtitle") globalsToAdd.AddRange(_cache.Globals.Subtitle);
        }

        globalsToAdd.AddRange(_cache.Globals.PerStream);

        foreach (var (k, v) in globalsToAdd)
        {
            if (!_allItems.Any(x => x.Key == k))
                _allItems.Add(new PickerItem(k, v.Description ?? "Global Option", new PickerResult(k, v), IsGlobal: true));
        }

        // 3. --- Apply Sorting ---
        _allItems = [.. _allItems
        .OrderBy(i => i.IsGlobal) // Format/Codec specific first
        .ThenBy(i => i.Key)];
    }

    private void _loadLanguages()
    {
        _allItems.Clear();

        // Try to treat _contextData as the language dictionary
        if (_contextData is Dictionary<string, string> languages)
        {
            foreach (var (code, name) in languages)
            {
                _allItems.Add(new PickerItem(code, name, new PickerResult(code, name)));
            }
        }

        // Fallback if no dictionary was provided
        _allItems.Add(new PickerItem("und", "Language list not loaded", new PickerResult("und", null!)));

        // Sort alphabetically by language name
        _allItems = _allItems.OrderBy(x => x.Description).ToList();
    }

    private void _updateFilter()
    {
        while (_listBox.GetFirstChild() is Widget child) _listBox.Remove(child);

        string query = _searchEntry.GetText().ToLower();
        var filtered = _allItems.Where(i =>
            i.Key.ToLower().Contains(query) ||
            (i.Description?.ToLower().Contains(query) ?? false)
        );

        foreach (var item in filtered)
        {
            var row = new PickerRow { Data = item.RawData };
            var box = new Box { MarginStart = 10, MarginEnd = 10, MarginTop = 5, MarginBottom = 5 };
            box.SetOrientation(Orientation.Vertical);

            // Create a horizontal box for the Title and the Badge
            var titleBox = new Box { Spacing = 6 };
            titleBox.SetOrientation(Orientation.Horizontal);

            var lblKey = new Label { Label_ = $"<b>{item.Key}</b>", UseMarkup = true, Xalign = 0 };
            titleBox.Append(lblKey);

            // If it's a global parameter, add a subtle badge
            if (item.IsGlobal)
            {
                var badge = new Label { Label_ = "Global" };
                badge.AddCssClass("badge"); // Ensure this is defined in your CSS
                badge.AddCssClass("dim-label");
                badge.SetOpacity(0.5);
                titleBox.Append(badge);
            }

            box.Append(titleBox);

            if (!string.IsNullOrEmpty(item.Description))
            {
                var lblDesc = new Label { Label_ = item.Description, Xalign = 0, Opacity = 0.7, Ellipsize = Pango.EllipsizeMode.End };
                lblDesc.AddCssClass("caption");
                box.Append(lblDesc);
            }

            row.SetChild(box);
            _listBox.Append(row);
        }
    }

    private string _getOptionValueString(IFFmpegValue? value)
    {
        return value switch
        {
            FFmpegValueLong v => v.Value.ToString(),
            FFmpegValueDouble v => v.Value.ToString("G"),
            FFmpegValueString v => v.Value,
            _ => "N/A"
        };
    }
}