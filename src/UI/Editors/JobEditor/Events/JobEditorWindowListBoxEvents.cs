using FFGui.Models;
using Gtk;

namespace FFGui.UI;

public partial class JobEditorWindow
{
    private void _onListSelectionChanged(string page, string listName, int selectedIndex)
    {
#if VERBOSE
        Console.WriteLine($"{page}.{listName} selected index: {selectedIndex}");
#endif
        switch (page)
        {
            case "pgStreams":
                switch (listName)
                {
                    case "lstStreams":
                        var lb = _getStreamListBox();
                        var selectedRow = lb?.GetSelectedRow();

                        // Check if we had a valid previous selection that needs saving
                        if (_selectedStream.f >= 0 && _selectedStream.s >= 0 && _job != null)
                        {
                            // Get the "Old" stream (using the OLD _selectedStream index)
                            // We need to be careful: if the user deleted a file/stream, indices might be invalid.
                            if (_selectedStream.f < _job.Sources.Count &&
                                _selectedStream.s < _job.Sources[_selectedStream.f].Streams.Count)
                            {
                                var oldStream = _job.Sources[_selectedStream.f].Streams[_selectedStream.s];

                                // Scrape the UI (which still shows old data) into the oldStream
                                _saveStreamSetupUI(oldStream);
                            }
                        }

                        if (selectedRow is StreamRow sRow)
                        {
#if VERBOSE
                            Console.WriteLine($"Selected File Index: {sRow.FileIndex}");
                            Console.WriteLine($"Selected Stream Index: {sRow.StreamIndex}");
#endif

                            _selectedStream = (sRow.FileIndex, sRow.StreamIndex);

                            var stream = _job?.Sources[_selectedStream.f].Streams[_selectedStream.s];
                            _updateStreamSetupUI(stream!);
                        }
                        break;
                }
                break;
        }
    }

    private void SyncMetadata(ListBox lb, Dictionary<string, string> targetDict)
    {
        if (_isUpdatingUi) return;

        targetDict.Clear();
        var child = lb.GetFirstChild();
        while (child != null)
        {
            // Assuming JobEditorUiFactory.CreateMetadataRow returns a row 
            // that exposes its Key and Value through widgets or properties.
            if (child is ListBoxRow row && row.GetChild() is Box box)
            {
                // This part depends on how your MetadataRow is structured internally.
                // Usually, it's a Box containing two Entries.
                var entries = new List<Entry>();
                _findEntriesRecursive(box, entries);

                if (entries.Count >= 2)
                {
                    string key = entries[0].Text_!;
                    string val = entries[1].Text_!;
                    if (!string.IsNullOrEmpty(key))
                    {
                        targetDict[key] = val;
                    }
                }
            }
            child = child.GetNextSibling();
        }
    }

    // Helper to find Gtk.Entry widgets inside the custom rows
    private void _findEntriesRecursive(Widget widget, List<Entry> found)
    {
        if (widget is Entry entry) found.Add(entry);
        else if (widget is Box box)
        {
            var child = box.GetFirstChild();
            while (child != null)
            {
                _findEntriesRecursive(child, found);
                child = child.GetNextSibling();
            }
        }
    }

    private void _saveStreamSetupUI(Job.Source.Stream stream)
    {
        // Encoder Tab
        var entEncoder = _getWidgetByPageAndPath<Entry>("pgStreams", "pgStreamEncoder", "entEncoder");
        if (entEncoder != null) stream.EncoderSettings.Encoder = entEncoder.GetText();

        // Force sync the Encoder Parameters ListBox
        // We pass ignoreLock: true because we want to force the read even if UI flags are set
        _syncEncoderParamsToJob(ignoreLock: true);

        // Filters Tab
        var ddFilterMode = _getWidgetByPageAndPath<DropDown>("pgStreams", "pgStreamFilters", "ddFilterMode");
        if (ddFilterMode != null)
        {
            stream.EncoderSettings.UsesComplexFilters = ddFilterMode.Selected == 1;
        }
        // Note: Filter list is usually managed by Add/Remove buttons directly, 
        // so we don't scrape the list here unless you allow inline editing of the list items directly.

        // Trim Tab
        var entTrimStart = _getWidgetByPageAndPath<Entry>("pgStreams", "pgStreamTrim", "entTrimStart");
        if (entTrimStart != null) stream.Trim.Start = entTrimStart.GetText();

        var entTrimLength = _getWidgetByPageAndPath<Entry>("pgStreams", "pgStreamTrim", "entTrimLength");
        if (entTrimLength != null) stream.Trim.Length = entTrimLength.GetText();

        var entTrimEnd = _getWidgetByPageAndPath<Entry>("pgStreams", "pgStreamTrim", "entTrimEnd");
        if (entTrimEnd != null) stream.Trim.End = entTrimEnd.GetText();

        // Metadata Tab
        var lbStreamMeta = _getWidgetByPageAndPath<ListBox>("pgStreams", "pgStreamMetadata", "lbMSMetadata");
        if (lbStreamMeta != null)
        {
            // This helper (from your provided code) scrapes the UI rows and updates the Dictionary
            SyncMetadata(lbStreamMeta, stream.Metadata);
        }

        // Parameters Tab
        var entLanguage = _getWidgetByPageAndPath<Entry>("pgStreams", "pgStreamParameters", "entLanguage");
        if (entLanguage != null) stream.Language = entLanguage.GetText();

        var entDelay = _getWidgetByPageAndPath<Entry>("pgStreams", "pgStreamParameters", "entDelay");
        if (entDelay != null) stream.Delay = entDelay.GetText();

        // Note: Dispositions (FlowBox) are updated immediately by their pill remove buttons, 
        // so no need to scrape them here.
    }

    /// <summary>
    /// Populates all sub-tabs (Encoder, Filters, Trim, etc.) with the current stream's data.
    /// </summary>
    private void _updateStreamSetupUI(Job.Source.Stream stream)
    {
        // --- Encoder Tab ---
        var entEncoder = _getWidgetByPageAndPath<Entry>("pgStreams", "pgStreamEncoder", "entEncoder");
        entEncoder?.SetText(stream.EncoderSettings.Encoder);

        // Refresh Encoder Parameters List
        var lbEP = _getWidgetByPageAndPath<ListBox>("pgStreams", "pgStreamEncoder", "lbESEncoderParams");
        if (lbEP != null)
        {
            _isUpdatingUi = true;

            // Clear existing rows
            while (lbEP.GetFirstChild() is Widget child) lbEP.Remove(child);

            // Lookup the codec schema to get parameter types/min/max/options
            FFmpegCodec? codecSchema = null;
            if (!string.IsNullOrEmpty(stream.EncoderSettings.Encoder))
            {
                _app.Cache.Codecs.TryGetValue(stream.EncoderSettings.Encoder, out codecSchema);
            }

            stream.EncoderSettings.Parameters ??= [];
            foreach (var param in stream.EncoderSettings.Parameters)
            {
                string paramKey = param.Key;
                object? paramValue = param.Value;

                // Try to find schema in codec or globals
                FFmpegParameter? schema = null;
                codecSchema?.Parameters.TryGetValue(paramKey, out schema);

                // If not in codec, check stream-type globals (Video/Audio/Subtitle) or PerStream globals
                if (schema == null)
                {
                    if (stream.Type == "video") _app.Cache.Globals.Video.TryGetValue(paramKey, out schema);
                    else if (stream.Type == "audio") _app.Cache.Globals.Audio.TryGetValue(paramKey, out schema);
                    else if (stream.Type == "subtitle") _app.Cache.Globals.Subtitle.TryGetValue(paramKey, out schema);

                    if (schema == null) _app.Cache.Globals.PerStream.TryGetValue(paramKey, out schema);
                }

                var row = ParameterRowFactory.CreateParameterRow(
                    paramKey,
                    paramValue,
                    schema,
                    lbEP.Remove,
                    () => { }
                );

                lbEP.Append(row);
                row.Show();
            }
        }

        // --- Filters Tab ---
        var ddFilterMode = _getWidgetByPageAndPath<DropDown>("pgStreams", "pgStreamFilters", "ddFilterMode");
        if (ddFilterMode != null)
        {
            _isUpdatingUi = true;
            // Simple = 0, Complex = 1
            ddFilterMode.Selected = stream.EncoderSettings.UsesComplexFilters ? 1u : 0u;

            // Connect the change event to the model
            ddFilterMode.OnNotify += (s, e) =>
            {
                if (e.Pspec.GetName() == "selected" && !_isUpdatingUi)
                {
                    stream.EncoderSettings.UsesComplexFilters = ddFilterMode.Selected == 1;
                }
            };
        }

        var lbFilters = _getWidgetByPageAndPath<ListBox>("pgStreams", "pgStreamFilters", "listSimpleFilters");

        if (lbFilters != null)
        {
            while (lbFilters.GetFirstChild() is Widget child) lbFilters.Remove(child);

            foreach (var filter in stream.EncoderSettings.Filters)
            {
                var row = JobEditorUiFactory.CreateFilterRow(filter,
                    (r) =>
                    {
                        stream.EncoderSettings.Filters.Remove(filter);
                        lbFilters.Remove(r);
                    },
                    () =>
                    {
                        // Find schema in cache to provide to editor
                        if (_app.Cache.Filters.TryGetValue(filter.FilterName, out var schema))
                        {
                            var editor = new FilterParameterEditor(_app, this, filter, schema, () =>
                            {
                                // Refresh the UI row summary after editing
                                _updateStreamSetupUI(stream);
                            });
                            editor.Present();
                        }
                    }
                );
                lbFilters.Append(row);
            }
        }

        // --- Trim Tab ---
        _getWidgetByPageAndPath<Entry>("pgStreams", "pgStreamTrim", "entTrimStart")?.SetText(stream.Trim.Start);
        _getWidgetByPageAndPath<Entry>("pgStreams", "pgStreamTrim", "entTrimLength")?.SetText(stream.Trim.Length);
        _getWidgetByPageAndPath<Entry>("pgStreams", "pgStreamTrim", "entTrimEnd")?.SetText(stream.Trim.End);

        // --- Metadata Tab (Stream & Container) ---
        var lbStreamMeta = _getWidgetByPageAndPath<ListBox>("pgStreams", "pgStreamMetadata", "lbMSMetadata");
        if (lbStreamMeta != null)
        {
            _isUpdatingUi = true;
            while (lbStreamMeta.GetFirstChild() is Widget child) lbStreamMeta.Remove(child);

            foreach (var entry in stream.Metadata)
            {
                string key = entry.Key;
                ListBoxRow row = null!;
                // Pass the sync method as a callback for when the text changes
                row = JobEditorUiFactory.CreateMetadataRow(key, entry.Value.ToString() ?? "", 
                    () => { lbStreamMeta.Remove(row); SyncMetadata(lbStreamMeta, stream.Metadata); }, // On Remove
                    () => { SyncMetadata(lbStreamMeta, stream.Metadata); } // On Changed (Makes sure factory supports this)
                );
                lbStreamMeta.Append(row);
            }
        }

        var lbContainerMeta = _getWidgetByPageAndPath<ListBox>("pgContainer", "lbCSMetadata");
        if (lbContainerMeta != null)
        {
            // Initial Phase Copy: Only copy if Job Metadata is empty and we have sources
            if (_job.Metadata.Count == 0 && _job.Sources.Count > 0)
            {
                foreach (var entry in _job.Sources[0].Metadata)
                {
                    _job.Metadata[entry.Key] = entry.Value;
                }
            }

            // Clear UI
            while (lbContainerMeta.GetFirstChild() is Widget child) lbContainerMeta.Remove(child);

            // Populate from _job.Metadata (NOT source anymore)
            foreach (var entry in _job.Metadata)
            {
                string key = entry.Key;
                ListBoxRow row = null!;
                row = JobEditorUiFactory.CreateMetadataRow(key, entry.Value,
                    () =>
                    {
                        _job.Metadata.Remove(key);
                        _updateStreamSetupUI(stream);
                    },
                    () => { }
                );
                lbContainerMeta.Append(row);
            }
        }

        // --- Parameters Tab ---
        _getWidgetByPageAndPath<Entry>("pgStreams", "pgStreamParameters", "entLanguage")?.SetText(stream.Language);
        _getWidgetByPageAndPath<Entry>("pgStreams", "pgStreamParameters", "entDelay")?.SetText(stream.Delay);

        // Populate Dispositions FlowBox
        var fbDisp = _getWidgetByPageAndPath<FlowBox>("pgStreams", "pgStreamParameters", "fbDisposition");
        if (fbDisp != null)
        {
            // Clear existing pills
            while (fbDisp.GetFirstChild() is Widget child) fbDisp.Remove(child);

            // Add current pills from Job model
            foreach (var disp in stream.Disposition)
            {
                // Capture local copy for the closure
                string currentDisp = disp;

                // Pass the 3 required arguments to match the updated Factory signature
                var pill = JobEditorUiFactory.CreatePill(
                    text: currentDisp,
                    widgets: new Dictionary<string, object>(), // Pass empty dict as the 2nd param
                    onRemove: () =>
                    {
                        // Logic to remove from model and refresh UI
                        stream.Disposition.Remove(currentDisp);
                        _refreshDispositionFlowBox(stream);
                    }
                );

                fbDisp.Append(pill);
            }
        }

        GLib.Functions.IdleAdd(0, () =>
        {
            _isUpdatingUi = false;
            return false;
        });
    }
}
