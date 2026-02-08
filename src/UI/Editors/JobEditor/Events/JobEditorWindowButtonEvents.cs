namespace FFGui.UI;

using FFGui.Models;
using GLib;
using GLib.Internal;
using Gtk;

public partial class JobEditorWindow
{
    private void _onPageButtonClicked(string page, string button)
    {
        if (_job == null)
        {
            Console.WriteLine($"WARNING: {page}.{button} clicked, BUT _job is null! Event aborted.");
            return;
        }
#if VERBOSE
        Console.WriteLine($"{page}.{button} clicked.");
#endif
        // --- GLOBAL ACTIONS ---
        // These actions don't need a selected stream
        if (page == "main")
        {
            switch (button)
            {
                case "applyButton":
                case "createButton":
                    // Sync main settings
                    var entJobName = _getWidgetByPageAndPath<Entry>("", "entJobName");
                    if (entJobName is not null)
                        _job.Name = entJobName.Text_ ??= "";

                    var entOutputDir = _getWidgetByPageAndPath<Entry>("", "entOutputDir");
                    if (entOutputDir is not null)
                        _job.OutputDirectory = entOutputDir.Text_ ??= "";

                    var entOutputFn = _getWidgetByPageAndPath<Entry>("", "entOutputFn");
                    if (entOutputFn is not null)
                        _job.OutputFileName = entOutputFn.Text_ ??= "";

                    // Sync UI to data for currently editing stream
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

                    if (_mode == EditorMode.Clone)
                    {
                        _onSuccess.Invoke(_job!);
                    }
                    else
                    {
                        _originalJob.UpdateFrom(_job!);
                        _onSuccess.Invoke(_originalJob);
                    }
                    Close();
                    return;
                case "cancelButton":
                    Close();
                    return;
            }
            return;
        }

        if (page == "pgSources")
        {
            // Get the ListBox widget from the _pages structure
            var lb = _getSourceListBox();
            if (lb == null)
            {
                Console.WriteLine($"WARNING: Source ListBox not found! Aborting event.");
                return;
            }

            switch (button)
            {
                case "btnAdd":
                    //Add files to source list

                    // Create the File Chooser
                    var chooser = FileChooserNative.New(
                        "Select Media Files",
                        this,
                        FileChooserAction.Open,
                        "Open",
                        "Cancel"
                    );

                    // Allow multiple selection
                    chooser.SelectMultiple = true;

                    // Add common media filters
                    var filter = FileFilter.New();
                    filter.SetName("Media Files");
                    filter.AddMimeType("video/*");
                    filter.AddMimeType("audio/*");
                    chooser.AddFilter(filter);

                    chooser.OnResponse += (s, e) =>
                    {
                        if (e.ResponseId == (int)ResponseType.Accept)
                        {
                            var files = chooser.GetFiles();
                            var paths = new List<string>();

                            for (uint i = 0; i < files.GetNItems(); i++)
                            {
                                // Explicitly grab the pointer
                                nint ptr = files.GetItem(i);

                                if (ptr != nint.Zero)
                                {
                                    // Wrap the pointer into a FileHelper/FileImpl
                                    var handle = new GObject.Internal.ObjectHandle(ptr, false);
                                    var file = new Gio.FileHelper(handle);

                                    string? path = file.GetPath();
                                    if (!string.IsNullOrEmpty(path))
                                        paths.Add(path);
                                }
                            }

                            if (paths.Count > 0)
                            {
                                _ = _addSourceFiles(paths, lb);
                            }
                        }
                        chooser.Destroy();
                    };
                    chooser.Show();
                    break;
                case "btnRm":
                    var selectedRow = lb?.GetSelectedRow();
                    if (lb != null && selectedRow != null && _job != null)
                    {
                        int index = selectedRow.GetIndex();

                        // Keep indices in sync: remove from data first, then UI
                        if (index >= 0 && index < _job.Sources.Count)
                        {
                            _job.Sources.RemoveAt(index);
                            lb.Remove(selectedRow);
                            _refreshStreamList();
                        }
                    }
                    break;
                case "btnUp":
                    var rowUp = lb.GetSelectedRow();
                    if (rowUp != null && _job != null)
                    {
                        int index = rowUp.GetIndex();
                        if (index > 0)
                        {
                            // Sync Data Model (Swap positions)
                            var item = _job.Sources[index];
                            _job.Sources.RemoveAt(index);
                            _job.Sources.Insert(index - 1, item);

                            // Extract child, destroy row, re-insert
                            var childWidget = rowUp.GetChild();
                            rowUp.SetChild(null);
                            lb.Remove(rowUp);

                            // Inserting the childWidget directly forces GTK to create a NEW row
                            lb.Insert(childWidget!, index - 1);

                            // Select the new row
                            var newRow = lb.GetRowAtIndex(index - 1);
                            if (newRow != null)
                            {
                                lb.SelectRow(newRow);
                                newRow.GrabFocus();
                                _refreshStreamList();
                            }
                        }
                    }
                    break;

                case "btnDwn":
                    var rowDn = lb.GetSelectedRow();
                    if (rowDn != null && _job != null)
                    {
                        int index = rowDn.GetIndex();
                        if (index >= 0 && index < _job.Sources.Count - 1)
                        {
                            // Sync Data Model
                            var item = _job.Sources[index];
                            _job.Sources.RemoveAt(index);
                            _job.Sources.Insert(index + 1, item);

                            // Extract child, destroy row, re-insert
                            var childWidget = rowDn.GetChild();
                            rowDn.SetChild(null);
                            lb.Remove(rowDn);

                            // Inserting the childWidget directly forces GTK to create a NEW row
                            lb.Insert(childWidget!, index + 1);

                            // Select the new row
                            var newRow = lb.GetRowAtIndex(index + 1);
                            if (newRow != null)
                            {
                                lb.SelectRow(newRow);
                                newRow.GrabFocus();
                                _refreshStreamList();
                            }
                        }
                    }
                    break;

                case "btnClr":
                    if (_job != null && _job.Sources.Count > 0)
                    {
                        var dialog = new Gtk.MessageDialog()
                        {
                            TransientFor = this,
                            Modal = true,
                            DestroyWithParent = true,
                            MessageType = Gtk.MessageType.Question,
                            Text = "Are you sure you want to clear the source list?",
                            SecondaryText = "This will remove all analyzed files from the current job."
                        };

                        // -5 is the standard GTK ResponseType.Ok / Yes
                        // -6 is the standard GTK ResponseType.Cancel / No
                        dialog.AddButton("No", -6);
                        dialog.AddButton("Yes", -5);

                        dialog.OnResponse += (sender, args) =>
                        {
                            if (args.ResponseId == -5) // User clicked 'Yes'
                            {
                                _job.Sources.Clear();
                                _job.TotalDuration = 0;

                                while (lb.GetFirstChild() is Gtk.Widget child)
                                {
                                    lb.Remove(child);
                                    _refreshStreamList();
                                }
                            }
                            dialog.Destroy();
                        };

                        dialog.Show();
                    }
                    break;
                default:

                    break;
            }
            return;
        }

        // --- STREAM ACTIONS ---
        // This block needs a selected stream
        if (_selectedStream.f < 0 || _selectedStream.s < 0)
        {
            Console.WriteLine("WARNING: No stream selection! Aborting event.");
            return;
        }

        /* The indexes are set in JobEditorWindowListBoxEvents.cs when the user selects a stream
           or when the first file has been added and the first stream was automatically selected */
        var selectedStream = _job.Sources[_selectedStream.f].Streams[_selectedStream.s];
        
        switch (page)
        {
            case "pgSources":

                break;
            case "pgStreamEncoder":
                switch (button)
                {
                    case "btnESPickEncoder":
                        // 1. Safety Check: Ensure a stream is actually selected
                        if (_selectedStream.f < 0 || _selectedStream.s < 0) return;


                        var picker = new PickerWindow(_app.Cache, PickerType.Encoder, (obj) =>
                        {
                            // 2. Cast the object to PickerResult to access Key and Data
                            if (obj is PickerWindow.PickerResult result)
                            {
                                var codecName = result.Key;
#if VERBOSE
                                Console.WriteLine($"Picked: {codecName}");
#endif
                                // 3. Update the Model immediately
                                selectedStream.EncoderSettings.Encoder = codecName;

                                // 4. Update the UI on the next Idle cycle
                                GLib.Functions.IdleAdd(0, () =>
                                {
                                    _updateStreamSetupUI(selectedStream);
                                    return false;
                                });
                            }
                        }, streamType: selectedStream.Type);

                        picker.SetTransientFor(this);
                        picker.Present();
                        break;
                    case "btnESLoadTemplate":
                        if (selectedStream is not null)
                            TemplateApplier.LoadEncoderTemplate(this, _app, selectedStream.EncoderSettings, selectedStream.Type,
                                () => _updateStreamSetupUI(selectedStream));
                        break;
                    case "btnESAddParam":

                        // 1. Identify which encoder is currently selected for this stream
                        var codecName = selectedStream.EncoderSettings.Encoder;

                        if (string.IsNullOrEmpty(codecName) || !_app.Cache.Codecs.ContainsKey(codecName))
                        {
                            // Optional: Show a warning that an encoder must be selected first
                            return;
                        }

                        var codecSchema = _app.Cache.Codecs[codecName];

                        // 2. Open PickerWindow with the codec as context
                        var paramPicker = new PickerWindow(_app.Cache, PickerType.Parameter, (obj) =>
                        {
                            // FIX: Ensure we handle the PickerResult structure
                            if (obj is PickerWindow.PickerResult result && result.Data is FFmpegParameter paramSchema)
                            {
                                GLib.Functions.IdleAdd(0, () =>
                                {
                                    var lbEP = _getWidgetByPageAndPath<ListBox>("pgStreams", "pgStreamEncoder", "lbESEncoderParams");
                                    if (lbEP == null) return false;

                                    var newRow = ParameterRowFactory.CreateParameterRow(
                                        result.Key,
                                        paramSchema.Default,
                                        paramSchema,
                                        (r) => { lbEP.Remove(r); _syncEncoderParamsToJob(); },
                                        () => _syncEncoderParamsToJob(ignoreLock: true) // Standard value changes respect the lock
                                    );

                                    lbEP.Append(newRow);
                                    newRow.Show();

                                    // Bypass the lock to ensure this manual add is saved immediately
                                    _syncEncoderParamsToJob(ignoreLock: true);

                                    return false;
                                });
                            }
                        },
                        contextData: codecSchema,
                        streamType: selectedStream.Type
                    );

                    paramPicker.SetTransientFor(this);
                    paramPicker.Present();
                    break;
                }
                break;

            case "pgStreamFilters":
                var currentStream = _job.Sources[_selectedStream.f].Streams[_selectedStream.s];
                switch (button)
                {
                    case "btnFSLoadTemplate":
                        if (selectedStream is not null)
                            TemplateApplier.LoadEncoderTemplate(this, _app, selectedStream.EncoderSettings, selectedStream.Type,
                                () => _updateStreamSetupUI(selectedStream));
                        break;
                    case "btnFSAddFilter":
                        var filterPicker = new PickerWindow(_app.Cache, PickerType.Filter, (obj) =>
                        {
                            if (obj is PickerWindow.PickerResult result)
                            {
                                var filterName = result.Key;

                                // 1. Create the new filter settings object
                                var newFilter = new EncoderSettings.FilterSettings
                                {
                                    FilterName = filterName,
                                    Parameters = new Dictionary<string, object>()
                                };

                                // 2. Add to the Job Model
                                currentStream.EncoderSettings.Filters.Add(newFilter);

                                // 3. Immediately open the Parameter Editor to invite user input
                                if (_app.Cache.Filters.TryGetValue(filterName, out var schema))
                                {
                                    var editor = new FilterParameterEditor(_app, this, newFilter, schema, () =>
                                    {
                                        // This callback runs when 'Apply' is clicked in the editor
                                        _updateStreamSetupUI(currentStream);
                                    });
                                    editor.Present();
                                }

                                // 4. Refresh the background list so the user sees it was added
                                _updateStreamSetupUI(currentStream);
                            }
                        }, streamType: selectedStream.Type);

                        filterPicker.SetTransientFor(this);
                        filterPicker.Present();
                        break;
                    case "btnFSOpenGraph": break;
                }
                break;

            case "pgContainer":
                switch (button)
                {
                    case "btnCSSelectContainer":
                        var muxPicker = new PickerWindow(_app.Cache, PickerType.Muxer, (obj) =>
                        {
                            if (obj is PickerWindow.PickerResult result)
                            {
                                var newMuxer = result.Key;

                                // 1. Check if the container actually changed
                                if (_job.Multiplexer != newMuxer)
                                {
                                    // 2. Update the Model
                                    _job.Multiplexer = newMuxer;

                                    // 3. Reset Muxer Parameters (old parameters won't work with new muxer)
                                    _job.MuxerParameters?.Clear();

                                    // 4. Update UI
                                    GLib.Functions.IdleAdd(0, () =>
                                    {
                                        // Update the main container label/entry
                                        var entContainer = _getWidgetByPageAndPath<Entry>("pgContainer", "entCSContainerFormat");
                                        if (entContainer != null) entContainer.Text_ = newMuxer;

                                        // Clear the parameters ListBox
                                        var lbMP = _getWidgetByPageAndPath<ListBox>("pgContainer", "lbCSMuxerParams");
                                        if (lbMP != null)
                                        {
                                            while (lbMP.GetFirstChild() is Widget child) lbMP.Remove(child);
                                        }

                                        return false;
                                    });
                                }
                            }
                        });

                        muxPicker.SetTransientFor(this);
                        muxPicker.Present();
                        break;
                    case "btnCSLoadContainerTemplate":
                        if (_job is not null)
                            TemplateApplier.LoadContainerTemplate(this, _app, _job, _job.Multiplexer, _populateInitialData);
                        break;
                    case "btnCSAddMuxParam":
                        // 1. Identify the current muxer (format)
                        var muxerName = _job.Multiplexer;
                        if (string.IsNullOrEmpty(muxerName) || !_app.Cache.Formats.ContainsKey(muxerName))
                        {
                            var dialog = new MessageDialog()
                            {
                                TransientFor = this,
                                Modal = true,
                                DestroyWithParent = true,
                                MessageType = MessageType.Error,
                                Text = "No Container Selected",
                                SecondaryText = "Please select a container format (e.g., mp4, mkv) before adding muxer parameters."
                            };

                            // Add a Close/OK button
                            dialog.AddButton("OK", -5); // -5 is ResponseType.Ok

                            dialog.OnResponse += (s, e) => dialog.Destroy();
                            dialog.Show();
                            return;
                        }

                        var muxerSchema = _app.Cache.Formats[muxerName];

                        // 2. Open PickerWindow with the Format as context
                        var mParamPicker = new PickerWindow(_app.Cache, PickerType.Parameter, (obj) =>
                        {
                            if (obj is PickerWindow.PickerResult result && result.Data is FFmpegParameter paramSchema)
                            {
                                GLib.Functions.IdleAdd(0, () =>
                                {
                                    var lbMP = _getWidgetByPageAndPath<ListBox>("pgContainer", "lbCSMuxerParams");
                                    if (lbMP == null) return false;

                                    var newRow = ParameterRowFactory.CreateParameterRow(
                                        result.Key,
                                        paramSchema.Default,
                                        paramSchema,
                                        (r) => { lbMP.Remove(r); _syncMuxerParamsToJob(); },
                                        () => _syncMuxerParamsToJob(ignoreLock: true)
                                    );

                                    lbMP.Append(newRow);
                                    newRow.Show();

                                    _syncMuxerParamsToJob(ignoreLock: true);
                                    return false;
                                });
                            }
                        },
                        contextData: muxerSchema); // Context is the FFmpegFormat object

                        mParamPicker.SetTransientFor(this);
                        mParamPicker.Present();
                        break;
                    case "btnCSAddMetadata":
                        _addMetadataEntry("pgContainer", "", "lbCSMetadata", _job.Metadata);
                        break;
                }
                break;

            case "pgStreamMetadata":
                if (button == "btnMSAddParam")
                {
                    var stream = _job.Sources[_selectedStream.f].Streams[_selectedStream.s];
                    _addMetadataEntry("pgStreams", "pgStreamMetadata", "lbMSMetadata", selectedStream.Metadata);
                }
                break;

            case "pgStreamParameters":
                switch (button)
                {
                    case "btnPSPickLanguage":
                        var langPicker = new PickerWindow(
                            cache: _app.Cache,
                            type: PickerType.Language,
                            onPicked: (obj) =>
                            {
                                if (obj is PickerWindow.PickerResult result)
                                {
                                    var entLang = _getWidgetByPageAndPath<Entry>("pgStreams", "pgStreamParameters", "entLanguage");
                                    if (entLang != null) entLang.Text_ = result.Key;
                                }
                            },
                            parentKey: null,
                            contextData: _app.Languages // <--- Pass the Dict here!
                        );
                        langPicker.SetTransientFor(this);
                        langPicker.Present();
                        break;
                    case "btnPSAddDisposition":
                        var stream = _job.Sources[_selectedStream.f].Streams[_selectedStream.s];

                        // Filter options based on stream type (Video vs Audio)
                        var filteredOptions = _dispositionData
                            .Where(x => (stream.Type == "video" && x.Value.Video) ||
                                        (stream.Type == "audio" && x.Value.Audio) ||
                                        (stream.Type != "video" && stream.Type != "audio")) // Keep all for subs/data
                            .ToDictionary(x => x.Key, x => x.Value.Option);

                        // Convert current List<string> to a "+"-separated string for the Picker
                        string currentFlags = string.Join("+", stream.Disposition);

                        // Open the Picker Window
                        var picker = new FlagsPickerWindow("Disposition", filteredOptions, currentFlags, (result) =>
                        {
                            // Update the Model
                            stream.Disposition = [.. result.Split('+', StringSplitOptions.RemoveEmptyEntries)];

                            // Refresh the UI (FlowBox)
                            _refreshDispositionFlowBox(stream);
                        });

                        picker.SetTransientFor(this);
                        picker.Present();
                        break;
                    case "btnPSAddParam": break;
                }
                break;

            default:

                break;
        }
    }

    // Commons
    private void _addMetadataEntry(string page, string subPage, string listName, Dictionary<string, string> targetDict)
    {
        ListBox? lb = string.IsNullOrEmpty(subPage)
            ? _getWidgetByPageAndPath<ListBox>(page, listName)
            : _getWidgetByPageAndPath<ListBox>(page, subPage, listName);

        if (lb == null) return;

        string newKey = "new_tag_" + (targetDict.Count + 1);
        targetDict[newKey] = ""; // Initial model update

        ListBoxRow row = null!;
        row = JobEditorUiFactory.CreateMetadataRow(newKey, "",
            () =>
            {
                lb.Remove(row);
                SyncMetadata(lb, targetDict);
            },
            () =>
            {
                SyncMetadata(lb, targetDict);
            }
        );

        lb.Append(row);
        row.Show();

        // Sync immediately to lock in the new empty entry
        SyncMetadata(lb, targetDict);
    }

    private void _refreshDispositionFlowBox(Job.Source.Stream stream)
    {
        var fbDisp = _getWidgetByPageAndPath<FlowBox>("pgStreams", "pgStreamParameters", "fbDisposition");
        if (fbDisp == null) return;

        // Clear existing pills
        var child = fbDisp.GetFirstChild();
        while (child != null)
        {
            fbDisp.Remove(child);
            child = fbDisp.GetFirstChild();
        }

        foreach (var disp in stream.Disposition)
        {
            string currentDispValue = disp; // Capture for closure

            // Match the 3-parameter signature
            var pill = JobEditorUiFactory.CreatePill(
                currentDispValue,
                new Dictionary<string, object>(), // The 'widgets' param
                () =>
                {
                    stream.Disposition.Remove(currentDispValue);
                    _refreshDispositionFlowBox(stream);
                }
            );

            fbDisp.Append(pill);
        }
    }

    private void _syncEncoderParamsToJob(bool ignoreLock = false)
    {
#if VERBOSE
        Console.WriteLine($"Attempting to sync ... (Locked={_isUpdatingUi})");
#endif
        // 1. Check the gatekeeper (unless explicitly ignored)
        if (!ignoreLock && _isUpdatingUi) return;

        var lbEP = _getWidgetByPageAndPath<ListBox>("pgStreams", "pgStreamEncoder", "lbESEncoderParams");
        if (lbEP == null) return;

        // 2. Safely get the current stream
        var currentStream = _job.Sources[_selectedStream.f].Streams[_selectedStream.s];

        // 3. Fix the Null Reference Warning
        // Ensure the dictionary exists before we try to use it
        if (currentStream.EncoderSettings.Parameters == null)
            currentStream.EncoderSettings.Parameters = new Dictionary<string, object>();

        // 4. Collect rows into a list first (prevents collection-modified issues)
        var activeRows = new List<ParameterRow>();
        var child = lbEP.GetFirstChild();
        while (child != null)
        {
            if (child is ParameterRow row) activeRows.Add(row);
            child = child.GetNextSibling();
        }

        // 5. Update the model
        currentStream.EncoderSettings.Parameters.Clear();
        foreach (var row in activeRows)
        {
            object? val = ParameterRowFactory.ExtractWidgetValue(row.ValueWidget, row.Schema);
            if (val != null)
            {
                currentStream.EncoderSettings.Parameters[row.Key] = val;
            }
        }
#if VERBOSE
        Console.WriteLine($"Synced {currentStream.EncoderSettings.Parameters.Count} parameters (IgnoreLock: {ignoreLock}).");
#endif
    }

    private void _syncMuxerParamsToJob(bool ignoreLock = false)
    {
        if (!ignoreLock && _isUpdatingUi) return;

        var lbMP = _getWidgetByPageAndPath<ListBox>("pgContainer", "lbCSMuxerParams");
        if (lbMP == null) return;

        // Ensure the dictionary exists
        _job.MuxerParameters ??= new Dictionary<string, object>();
        _job.MuxerParameters.Clear();

        var child = lbMP.GetFirstChild();
        while (child != null)
        {
            if (child is ParameterRow row)
            {
                object? val = ParameterRowFactory.ExtractWidgetValue(row.ValueWidget, row.Schema);
                if (val != null)
                {
                    _job.MuxerParameters[row.Key] = val;
                }
            }
            child = child.GetNextSibling();
        }
    }
}
