namespace FFGui.UI;

using Gtk;
using FFGui.Core;
using FFGui.Models;

public partial class JobEditorWindow : Window
{
    public FFGuiApp _app;

    private static readonly Dictionary<string, (FFmpegOption Option, bool Video, bool Audio)> _dispositionData = new()
    {
        { "default", (new FFmpegOption { Description = "Primary stream selection" }, true, true) },
        { "dub", (new FFmpegOption { Description = "Dubbed version" }, false, true) },
        { "original", (new FFmpegOption { Description = "Original language version" }, true, true) },
        { "comment", (new FFmpegOption { Description = "Commentary track" }, true, true) },
        { "lyrics", (new FFmpegOption { Description = "Lyrics" }, false, false) },
        { "karaoke", (new FFmpegOption { Description = "Karaoke" }, true, true) },
        { "forced", (new FFmpegOption { Description = "Forced content" }, true, true) },
        { "hearing_impaired", (new FFmpegOption { Description = "For Hearing Impaired" }, true, true) },
        { "visual_impaired", (new FFmpegOption { Description = "For Visual Impaired" }, true, true) },
        { "clean_effects", (new FFmpegOption { Description = "Clean effects" }, false, true) },
        { "attached_pic", (new FFmpegOption { Description = "Album art / Cover" }, true, false) },
        { "timed_thumbnails", (new FFmpegOption { Description = "Timed thumbnails" }, true, false) },
        { "captions", (new FFmpegOption { Description = "Closed captions" }, true, false) },
        { "descriptions", (new FFmpegOption { Description = "Audio descriptions" }, false, true) },
        { "metadata", (new FFmpegOption { Description = "Metadata stream" }, true, true) },
        { "dependent", (new FFmpegOption { Description = "Dependent stream" }, true, true) },
        { "still_image", (new FFmpegOption { Description = "Static image" }, true, false) }
    };

    // DATA State
    private readonly EditorMode _mode;
    private readonly Job _originalJob;
    private readonly Job _job;
    private bool _isUpdatingUi;
    private Action<Job> _onSuccess;

    // UI State
    private (string Id, string Label, Dictionary<string, object> Widgets)[] _pages;
    private Dictionary<string, object> _widgets;
    private (int f, int s) _selectedStream = (-1, -1);

    private class StreamRow : ListBoxRow
    {
        public int FileIndex { get; init; }
        public int StreamIndex { get; init; }
    }

    public JobEditorWindow(Gtk.Application app, EditorMode mode, Job job, Action<Job> onSuccess)
    {
        // Setup context
        _app = (FFGuiApp)app;
        Application = app;

        _onSuccess = onSuccess;

        _mode = mode;
        _originalJob = job;
        _job = job.Clone();
        _pages = [];
        _widgets = [];

        BuildMainUI();
    }

    private void BuildMainUI()
    {
        _pages = [];
        _widgets = new();
        _isUpdatingUi = true;

        // Init main box
        var vbox = new Box()
        {
            MarginBottom = 8,
            MarginEnd = 8,
            MarginStart = 8,
            MarginTop = 8,
            Spacing = 8
        };
        vbox.SetOrientation(Orientation.Vertical);

        var buttonBox = new Box() { Spacing = 12, Halign = Align.End };
        buttonBox.SetOrientation(Orientation.Horizontal);

        // Setup window
        SetTitle($"{_mode.ToString()} Job");
        SetDefaultSize(1024, 500);
        SetSizeRequest(1024, 200);

        // Job name
        var labelGroup = new SizeGroup() { Mode = SizeGroupMode.Horizontal };

        var hbox = new Box() { Spacing = 8 };
        hbox.SetOrientation(Orientation.Horizontal);

        var label = new Label() { Label_ = "Job Name:", Xalign = 0, Halign = Align.Start };
        labelGroup.AddWidget(label);
        hbox.Append(label);

        var entJobName = new Entry() { Hexpand = true, Text_ = _job.Name };
        hbox.Append(entJobName);
        _widgets.Add(nameof(entJobName), entJobName);

        vbox.Append(hbox);

        var notebook = new Notebook()
        {
            Hexpand = true,
            Vexpand = true,
        };

        // Create pages
        _pages = [
            ("pgSources",       "Sources",      null!),
            ("pgStreams",       "Streams",      null!),
            ("pgContainer",     "Container",    null!)
        ];

        for (int i = 0; i < _pages.Length; i++)
        {
            var currentPage = _pages[i];
            int currentIndex = i;

            // Add page to notebook
            notebook.AppendPage(
                JobEditorUiFactory.BuildJobUI(currentPage.Id, _job, out _pages[currentIndex].Widgets),
                new Label() { Label_ = currentPage.Label }
            );

            // Register all page events
            _registerEvents(currentPage.Id, _pages[currentIndex].Widgets);
        }

        vbox.Append(notebook);

        // Output stuff
        var hboxOutputDir = new Box() { Spacing = 8 };
        hboxOutputDir.SetOrientation(Orientation.Horizontal);

        var lblOutputDir = new Label() { Label_ = "Output Directory:", Halign = Align.Start, Xalign = 0 };
        labelGroup.AddWidget(lblOutputDir);
        hboxOutputDir.Append(lblOutputDir);
        var entOutputDir = new Entry() { Hexpand = true, Text_ = _job.OutputDirectory };
        hboxOutputDir.Append(entOutputDir);
        _widgets.Add(nameof(entOutputDir), entOutputDir);
        vbox.Append(hboxOutputDir);

        var hboxOutputFn = new Box() { Spacing = 8 };
        hboxOutputFn.SetOrientation(Orientation.Horizontal);

        var lblOutputFn = new Label() { Label_ = "Output File Name:", Halign = Align.Start, Xalign = 0 };
        hboxOutputFn.Append(lblOutputFn);
        labelGroup.AddWidget(lblOutputFn);
        var entOutputFn = new Entry() { Hexpand = true, Text_ = _job.OutputFileName };
        hboxOutputFn.Append(entOutputFn);
        _widgets.Add(nameof(entOutputFn), entOutputFn);

        vbox.Append(hboxOutputFn);

        // Add buttons for editor
        switch (_mode)
        {
            case EditorMode.New:
            case EditorMode.Clone:
                var createButton = new Button() { Label = "Create" };
                createButton.AddCssClass("suggested-action");
                buttonBox.Append(createButton);
                _widgets.Add(nameof(createButton), createButton);
                break;
            case EditorMode.Edit:
                var applyButton = new Button() { Label = "Apply" };
                applyButton.AddCssClass("suggested-action");
                buttonBox.Append(applyButton);
                _widgets.Add(nameof(applyButton), applyButton);
                break;
        }

        var cancelButton = new Button() { Label = "Cancel" };
        cancelButton.AddCssClass("destructive-action");
        buttonBox.Append(cancelButton);
        _widgets.Add(nameof(cancelButton), cancelButton);

        vbox.Append(buttonBox);
        SetChild(vbox);

        // Register all main events
        _registerEvents("main", _widgets);

        _populateInitialData();

        _isUpdatingUi = false;
    }

    private void _populateInitialData()
    {
        _isUpdatingUi = true;

        // Fill Entry fields
        _getWidgetByPageAndPath<Entry>("", "entJobName")?.SetText(_job.Name ?? "");
        _getWidgetByPageAndPath<Entry>("", "entOutputDir")?.SetText(_job.OutputDirectory ?? "");
        _getWidgetByPageAndPath<Entry>("", "entOutputFn")?.SetText(_job.OutputFileName ?? "");

        // Set the Container Format Entry
        var entContainer = _getWidgetByPageAndPath<Entry>("pgContainer", "entCSContainerFormat");
        if (entContainer != null) entContainer.Text_ = _job.Multiplexer ?? "";

        // Load Muxer Parameters
        var lbMP = _getWidgetByPageAndPath<ListBox>("pgContainer", "lbCSMuxerParams");
        if (lbMP != null)
        {
            // Clear existing rows first
            while (lbMP.GetFirstChild() is Widget child) lbMP.Remove(child);

            // Get the muxer schema from the cache to provide context for the parameters
            FFmpegFormat? muxerSchema = null;
            if (!string.IsNullOrEmpty(_job.Multiplexer))
            {
                _app.Cache.Formats.TryGetValue(_job.Multiplexer, out muxerSchema);
            }

            if (_job.MuxerParameters != null)
            {
                foreach (var param in _job.MuxerParameters)
                {
                    // Try to find the specific schema for this parameter key
                    FFmpegParameter? paramSchema = null;
                    muxerSchema?.Parameters.TryGetValue(param.Key, out paramSchema);

                    // Create the row using our updated Factory (which now handles the new Flags logic)
                    var row = ParameterRowFactory.CreateParameterRow(
                        key: param.Key,
                        value: param.Value,
                        schema: paramSchema,
                        onRemove: (r) =>
                        {
                            lbMP.Remove(r);
                            _syncMuxerParamsToJob();
                        },
                        onChanged: () => _syncMuxerParamsToJob()
                    );

                    lbMP.Append(row);
                }
            }
        }

        // Fill the Sources ListBox
        var sourceLb = _getSourceListBox();
        if (sourceLb != null)
        {
            foreach (var source in _job.Sources)
            {
                var row = new ListBoxRow();
                row.SetChild(new Label() { Label_ = source.FileName, Halign = Align.Start });
                sourceLb.Append(row);
            }
        }

        // Fill the Streams ListBox (using your existing logic)
        _refreshStreamList();

        // Select the first stream
        var lb = _getStreamListBox();
        if (lb != null && lb.GetFirstChild() is Widget firstRow)
        {
            // Skip the header row and select the first actual stream row
            var streamRow = lb.GetRowAtIndex(1);
            if (streamRow != null) lb.SelectRow(streamRow);
        }

        _isUpdatingUi = false;
    }

    private async Task _addSourceFiles(List<string> filePaths, ListBox listBox)
    {
        if (filePaths.Count == 0) return;
        if (_job == null) return;
        _job.SetProbePath(_app.FFProbePath);

        await _job.AddSourceFilesAsync(filePaths);

        GLib.Functions.IdleAdd(0, () =>
        {
            _isUpdatingUi = true;
            _getWidgetByPageAndPath<Entry>("", "entJobName")?.SetText(_job.Name);

            while (listBox.GetFirstChild() is Widget child)
                listBox.Remove(child);

            foreach (var source in _job.Sources)
            {
                var row = new ListBoxRow();
                row.SetChild(new Label() { Label_ = source.FileName, Halign = Align.Start });
                listBox.Append(row);
            }
            _refreshStreamList();
            _isUpdatingUi = false;
            return false;
        });
    }

    private void _refreshStreamList()
    {
        var lb = _getStreamListBox();
        if (lb == null || _job == null) return;

        // 1. Clear existing items
        while (lb.GetFirstChild() is Widget child)
            lb.Remove(child);

        // 2. Rebuild the list
        for (int i = 0; i < _job.Sources.Count; i++)
        {
            var source = _job.Sources[i];

            // --- HEADER ROW (The File) ---
            var headerRow = new ListBoxRow();
            headerRow.SetSelectable(false);
            headerRow.SetActivatable(false);
            headerRow.AddCssClass("sidebar-header-row");

            // Label Setup for Ellipsing
            var headerLabel = new Label()
            {
                Label_ = $"<b><span face=\"'JetBrainsMono NL', monospace\">{i}:</span> {source.FileName}</b>",
                UseMarkup = true,
                Xalign = 0,
                MarginStart = 4,
                MarginTop = 4,
                MarginBottom = 4,
                MarginEnd = 4,
                Hexpand = true,
                Ellipsize = Pango.EllipsizeMode.Middle
            };
            headerRow.SetChild(headerLabel);
            lb.Append(headerRow);

            // --- CHILD ROWS (The Streams) ---
            for (int j = 0; j < source.Streams.Count; j++)
            {
                var stream = source.Streams[j];

                // Use our custom class to store indices
                var streamRow = new StreamRow
                {
                    FileIndex = i,
                    StreamIndex = j
                };

                streamRow.SetSelectable(stream.Active);

                var grid = new Grid()
                {
                    ColumnSpacing = 8,
                    RowSpacing = 2,
                    MarginStart = 32,
                    MarginTop = 4,
                    MarginBottom = 4,
                    MarginEnd = 4
                };

                // Checkbox
                var chkActive = new CheckButton() { Active = stream.Active, Valign = Align.Start };
                chkActive.OnToggled += (s, e) =>
                {
                    stream.Active = chkActive.Active;
                    streamRow.SetSelectable(chkActive.Active);
                };
                grid.Attach(chkActive, 0, 0, 1, 1);

                var lblStreamId = new Label()
                {
                    Label_ = $"<span face=\"'JetBrainsMono NL', monospace\">{i}.{stream.Index}:</span>",
                    UseMarkup = true
                };
                grid.Attach(lblStreamId, 1, 0, 1, 1);

                // Stream Info Labels with Ellipsing
                var lblInfo = new Label()
                {
                    Label_ = stream.DescriptionCodec,
                    Xalign = 0,
                    Hexpand = true,
                    Ellipsize = Pango.EllipsizeMode.Middle
                };
                grid.Attach(lblInfo, 2, 0, 1, 1);

                var lblInfo2 = new Label()
                {
                    Label_ = stream.DescriptionCodecExtended,
                    Xalign = 0,
                    Hexpand = true,
                    Ellipsize = Pango.EllipsizeMode.Middle
                };
                grid.Attach(lblInfo2, 2, 1, 1, 1);

                streamRow.SetChild(grid);
                lb.Append(streamRow);
            }
        }

        GLib.Functions.IdleAdd(0, () =>
        {
            // Look for the first row that is a StreamRow (skipping header rows)
            var firstRow = lb.GetRowAtIndex(1);
            if (firstRow is StreamRow sr)
            {
                lb.SelectRow(sr);
                // Manually trigger the selection state update
                _selectedStream = (sr.FileIndex, sr.StreamIndex);

                // Optional: Update the UI to reflect this stream's settings
                var target = _job.Sources[sr.FileIndex].Streams[sr.StreamIndex];
                _updateStreamSetupUI(target);
            }
            return false;
        });
    }
}
