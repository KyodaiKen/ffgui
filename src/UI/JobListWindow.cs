namespace FFGui.UI;

using Gtk;
using Gio;
using Gdk;
using GLib;
using HarfBuzz;

using System.Threading.Tasks;
using Task = System.Threading.Tasks.Task;

using FFGui.Core;
using FFGui.Models;

class JobListWindow : Window
{
    private FFGuiApp _app;
    private ScrolledWindow _jobListBoxScroller;
    private ListBox _jobListBox;
    private readonly Dictionary<int, JobRow> _jobRows = new();
    private Button _retryFailedButton;
    private Button _startButton;
    private Button _stopButton;
    private JobRunner _runner;

    private bool _isWaitingForStop = false;

    public JobListWindow(Gtk.Application app)
    {
        // Setup context
        _app = (FFGuiApp)app;
        Application = app;

        IconName = "de.kyo.ffgui";

        // Setup window
        SetTitle("FFgui");
        SetDefaultSize(640, 480);
        SetSizeRequest(640, 480);

        OnCloseRequest += _handleCloseRequest;

        // --- Custom header bar with menu button ---
        var header_bar = new Gtk.HeaderBar() { };
        SetTitlebar(header_bar);

        // Handle the menu separately
        var builder = Builder.NewFromString(Menus.JobListWindowMainMenu, Menus.JobListWindowMainMenu.Length);
        if (builder.GetObject("app-menu") is Gio.MenuModel main_menu_mdl)
        {
            var menu_button = new Gtk.MenuButton
            {
                IconName = "open-menu-symbolic",
                MenuModel = main_menu_mdl
            };
            header_bar.PackEnd(menu_button);
        }
        else
        {
            Console.WriteLine("Error: Could not find 'app-menu' in GtkBuilder string.");
        }

        // Initialize buttons
        _retryFailedButton = new() { Label = "Retry Failed", Visible = false };
        _retryFailedButton.OnClicked += OnButtonRetryFailedClicked;

        _startButton = new() { Label = "Start" };
        _startButton.AddCssClass("suggested-action");
        _startButton.OnClicked += OnStartButtonClicked;

        _stopButton = new Button { IconName = "media-playback-stop-symbolic", Visible = false };
        _stopButton.AddCssClass("destructive-action");
        _stopButton.OnClicked += _onStopClicked;

        // Create a box to hold your action buttons
        var actionBox = new Box { Spacing = 6, MarginEnd = 12 }; // Set spacing in pixels here
        actionBox.SetOrientation(Orientation.Horizontal);

        // Add your buttons to the Box instead of the HeaderBar directly
        actionBox.Append(_stopButton);
        actionBox.Append(_startButton);
        actionBox.Append(_retryFailedButton);

        // Pack the entire Box into the HeaderBar
        header_bar.PackEnd(actionBox);

        // Prepare main menu actions
        List<(string Name, Action<SimpleAction, Variant?> Callback)> actions = new() {
            ("open_joblist", (a, v) => OnOpenJobList(a, v)),
            ("save_joblist", OnSaveJobList),
            ("clear_joblist", (a, v) => _ = OnClearJobList(a, v)),
            ("create_job", OnCreateJob),
            ("create_jobs_from_dir", OnCreateJobsFromDir),
            ("pref", OnPref),
            ("tplm", OnTplManager),
            ("about", OnAbout),
            ("quit", OnQuit)
        };

        // Register menu entries
        var actionGroup = Gio.SimpleActionGroup.New();
        foreach (var (name, callback) in actions)
        {
            var action = Gio.SimpleAction.New(name, null);
            action.OnActivate += (sender, args) => callback(action, args.Parameter);
            actionGroup.AddAction(action);
        }
        InsertActionGroup("win", actionGroup);

        // --- Main Box ---
        var boxOuter = new Box();
        boxOuter.SetOrientation(Orientation.Vertical);
        boxOuter.Vexpand = true;
        boxOuter.Spacing = 2;
        boxOuter.MarginStart = 6;
        boxOuter.MarginEnd = 6;
        boxOuter.MarginTop = 6;
        boxOuter.MarginBottom = 6;
        SetChild(boxOuter);

        // --- Job ListBox with ScrolledWindow ---
        _jobListBoxScroller = new() { Vexpand = true };
        _jobListBoxScroller.SetPolicy(PolicyType.Automatic, PolicyType.Automatic);

        _jobListBox = new();
        _jobListBox.SetSelectionMode(SelectionMode.Multiple);
        _jobListBox.SetActivateOnSingleClick(false);

        _jobListBoxScroller.SetChild(_jobListBox);
        boxOuter.Append(_jobListBoxScroller);

        // Add the drag gesture for file selection to the JobListBox
        var dragGesture = GestureDrag.New();
        dragGesture.SetPropagationPhase(PropagationPhase.Bubble);
        dragGesture.OnDragUpdate += OnDragUpdate;
        _jobListBox.AddController(dragGesture);

        // Setup drop target for our JobListBox
        var dropTarget = Gtk.DropTarget.New(Gdk.FileList.GetGType(), Gdk.DragAction.Copy);

        dropTarget.OnDrop += (sender, args) =>
        {
            var paths = new List<string>();

            // Get the raw pointer to the GdkFileList boxed record
            nint boxedPtr = args.Value.GetBoxed();
            if (boxedPtr == nint.Zero) return false;

            var listHandle = new GLib.Internal.SListUnownedHandle(boxedPtr);

            // Use Foreach with the proper Handle type
            GLib.Internal.SList.Foreach(listHandle, (filePtr, _) =>
                    {
                if (filePtr != nint.Zero)
                {
                    // In many GirCore versions, objects are created by passing the pointer
                    // to a specific constructor that takes an Internal Handle.
                    var handle = new GObject.Internal.ObjectHandle(filePtr, false);
                    var file = new Gio.FileHelper(handle);

                    // OR, if Gio.File is an interface, we use the concrete Impl:
                    // var file = new Gio.FileImpl(filePtr, false);

                    string? path = file.GetPath();
                    if (!string.IsNullOrEmpty(path))
                    {
                        paths.Add(path);
                    }
                }
            }, nint.Zero);

            if (paths.Count > 0)
            {
                // Kick off the threaded probing logic
                _ = _createJobsFromFileList(paths);
                return true;
            }

            return false;
        };

        _jobListBox.AddController(dropTarget);

        _runner = new JobRunner(_app);

        _runner.OnJobStarted += (id, job) =>
        {
            _refreshJobRow(id);
            ScrollToJob(id);
        };

        _runner.OnJobProgressUpdated += (id, job, info, progress) =>
        {
            GLib.Functions.IdleAdd(0, () =>
            {
                var row = _findRowById(id);
                row?.UpdateUI(info, progress);
                return false;
            });
        };

        _runner.OnJobFinished += (id, job) =>
        {
            GLib.Functions.IdleAdd(0, () =>
            {
                var row = _findRowById(id);
                row?.UpdateUI(job.Status == Job.JobStatus.Successful ? "Done" : "Failed", 1.0);
                return false;
            });
        };
    }

    /* ####### Drag events ####### */
    private void OnDragUpdate(GestureDrag sender, GestureDrag.DragUpdateSignalArgs args)
    {
        // Get the starting point of the drag
        if (!sender.GetStartPoint(out double startX, out double startY)) 
            return;

        // Determine the selection rectangle boundaries
        double offsetY = args.OffsetY;
        double rectTop = offsetY > 0 ? startY : startY + offsetY;
        double rectBottom = rectTop + Math.Abs(offsetY);

        // Check for Control key modifier
        // In GirCore, we get the current event from the gesture
        var currentEvent = sender.GetCurrentEvent();
        bool isCtrl = false;
        if (currentEvent != null)
        {
            var state = currentEvent.GetModifierState();
            isCtrl = state.HasFlag(ModifierType.ControlMask);
        }

        // Iterate through rows and check bounds
        var row = _jobListBox.GetFirstChild();
        while (row != null)
        {
            if (row is ListBoxRow lbr)
            {
                // Compute bounds relative to the ListBox
                if (lbr.ComputeBounds(_jobListBox, out var rect))
                {
                    double rowY = rect.GetY();
                    double rowHeight = rect.GetHeight();
                    double rowBottom = rowY + rowHeight;

                    // Check intersection
                    if (rowBottom >= rectTop && rowY <= rectBottom)
                    {
                        _jobListBox.SelectRow(lbr);
                    }
                    else if (!isCtrl)
                    {
                        _jobListBox.UnselectRow(lbr);
                    }
                }
            }
            row = row.GetNextSibling();
        }
    }

    /* ####### BUTTON CLICK EVENTS ####### */
    private async void OnButtonRetryFailedClicked(Button sender, EventArgs args)
    {
        _setUiLocked(true);
        _retryFailedButton.SetVisible(false);
        try
        {
            await _runner.RunQueueAsync(retryFailedOnly: true);
        }
        finally
        {
            _setUiLocked(false);
            _refreshRetryButtonVisibility();
        }
    }

    private async void OnStartButtonClicked(Button sender, EventArgs args)
    {
        _setUiLocked(true);
        try
        {
            _retryFailedButton.SetVisible(false);
            await _runner.RunQueueAsync(retryFailedOnly: false);
        }
        finally
        {
            _setUiLocked(false);
            _refreshRetryButtonVisibility();
        }
    }

    private void _onStopClicked(object? sender, EventArgs e)
    {
        if (_isWaitingForStop)
        {
            // Second click: Force kill everything
            _runner.Stop(force: true);
        }
        else
        {
            // First click: Graceful request
            _isWaitingForStop = true;
            _stopButton.IconName = "process-stop-symbolic"; // Change icon to indicate second click = kill
            _runner.Stop(force: false);
        }
    }

    /* ####### MENU CLICK EVENTS ####### */
    // Job List Related
    private async void OnOpenJobList(SimpleAction action, Variant? parameter)
    {
        if (!await ClearJobs()) return;

        var chooser = FileChooserNative.New(
            "Open Job List",
            this,
            FileChooserAction.Open,
            "Open",
            "Cancel"
        );

        var filter = FileFilter.New();
        filter.SetName("YAML Files");
        filter.AddPattern("*.yaml");
        filter.AddPattern("*.yml");
        chooser.AddFilter(filter);

        chooser.OnResponse += (s, e) =>
        {
            if (e.ResponseId == (int)ResponseType.Accept)
            {
                var file = chooser.GetFile();
                string path = file?.GetPath() ?? "";

                try
                {
                    // Load the dictionary using our generic extension
                    var loadedJobs = YamlExtensions.FromYamlFile<Dictionary<int, Job>>(path);
                    
                    foreach (var (key, job) in loadedJobs)
                    {
                        job.SetProbePath(_app.FFProbePath);
                    }
                    
                    if (loadedJobs != null)
                    {
                        _app.Jobs = loadedJobs;
                        _refreshJobListBox();
                    }
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"Failed to load job list: {ex.Message}");
                }
            }
            chooser.Destroy();
        };

        chooser.Show();
    }

    private void OnSaveJobList(SimpleAction action, Variant? parameter)
    {
        if (_app.Jobs == null || _app.Jobs.Count == 0) return;

        var chooser = FileChooserNative.New(
            "Save Job List",
            this,
            FileChooserAction.Save,
            "Save",
            "Cancel"
        );
        
        chooser.SetCurrentName("jobs.yaml");

        chooser.OnResponse += (s, e) =>
        {
            if (e.ResponseId == (int)ResponseType.Accept)
            {
                var file = chooser.GetFile();
                string path = file?.GetPath() ?? "";

                try
                {
                    // Serialize the entire dictionary to the chosen path
                    _app.Jobs.ToYaml(path);
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"Failed to save job list: {ex.Message}");
                }
            }
            chooser.Destroy();
        };

        chooser.Show();
    }

    private async Task OnClearJobList(SimpleAction action, Variant? parameter)
    {
        await ClearJobs();
    }

    private async Task<bool> ClearJobs()
    {
        if (_app.Jobs == null || _app.Jobs.Count == 0) return true;

        var alert = new AlertDialog 
        {
            Message = "Clear All Jobs?",
            Detail = "This will remove all items from the current queue."
        };
        alert.SetButtons(new string[] { "Cancel", "Clear" });
        alert.SetCancelButton(0); // Index of "Cancel"
        alert.SetDefaultButton(1); // Index of "Clear"

        try 
        {
            // ChooseAsync returns the index of the clicked button
            int response = await alert.ChooseAsync(this);

            if (response == 1) // User clicked "Clear"
            {
                _app.Jobs.Clear();
                _refreshJobListBox();
                return true;
            }
        }
        catch (Exception ex)
        {
            Console.WriteLine($"Dialog error: {ex.Message}");
        }

        return false;
    }

    //Job creation related
    private void OnCreateJob(SimpleAction action, Variant? parameter)
    {
        var newJob = new Job(_app.FFProbePath);
        var editor = new JobEditorWindow(_app, EditorMode.New, newJob, (confirmedJob) =>
        {
            var nextId = (_app.Jobs?.Count > 0) ? _app.Jobs.Keys.Max() + 1 : 1;
            _app.Jobs?.Add(nextId, confirmedJob);
            _refreshJobListBox();
        });
        editor.Present();
    }
    private void OnCreateJobsFromDir(SimpleAction action, Variant? parameter)
    {
        var chooser = FileChooserNative.New(
            "Select Directory",
            this,
            FileChooserAction.SelectFolder,
            "Open",
            "Cancel"
        );

        chooser.OnResponse += async (s, e) =>
        {
            if (e.ResponseId == (int)ResponseType.Accept)
            {
                // Get the folder on the UI thread before jumping to a background task
                var folder = chooser.GetFile();
                if (folder == null) return;

                string folderPath = folder.GetPath() ?? "";

                // Wrap the heavy work in Task.Run to satisfy 'async' and keep UI smooth
                var files = await Task.Run(() =>
                {
                    var fileList = new List<string>();
                    // Enumerate files in the directory
                    var enumerator = folder.EnumerateChildren("standard::name,standard::type", FileQueryInfoFlags.None, null);

                    while (enumerator?.NextFile(null) is FileInfo info)
                    {
                        if (info.GetFileType() == FileType.Regular)
                        {
                            fileList.Add(Path.Combine(folderPath, info.GetName()));
                        }
                    }
                    return fileList;
                });

                // Await the job creation (which you've already made async)
                await _createJobsFromFileList(files);
            }
            chooser.Destroy();
        };

        chooser.Show();
    }

    //App related
    private void OnPref(SimpleAction action, Variant? parameter)
    {
        var wndPref = new SettingsWindow(_app, this);
        this.SetSensitive(false);

        wndPref.OnCloseRequest += (sender, args) =>
        {
            this.SetSensitive(true);
            wndPref.Destroy();
            return false;
        };

        wndPref.Present();
    }

    private void OnTplManager(SimpleAction action, Variant? parameter)
    {
        var managerWin = new TemplateManagerWindow(_app, null!);
        managerWin.Present();
    }

    private void OnAbout(SimpleAction action, Variant? parameter)
    {
        var aboutWin = new AboutWindow(_app, this);
        aboutWin.Present();
    }

    private void OnQuit(SimpleAction action, Variant? parameter)
    {
        _app.Quit();
    }

    // --- Private methods ---
    private async Task _createJobsFromFileList(List<string> filePaths)
    {
        if (filePaths.Count == 0) return;

        using var cts = new CancellationTokenSource();
        ProgressWindow? progWin = null;
        bool isWindowShown = false;

        // Show progress window if creating MANY jobs takes time
        var timerTask = Task.Delay(500, cts.Token).ContinueWith(t =>
        {
            if (t.IsCanceled) return;
            GLib.Functions.IdleAdd(0, () =>
            {
                progWin = new ProgressWindow(this);
                progWin.OnCancelRequested += (s, e) => cts.Cancel();
                progWin.Show();
                isWindowShown = true;
                return false;
            });
        });

        try
        {
            int nextId = (_app.Jobs.Count == 0) ? 1 : _app.Jobs.Keys.Max() + 1;

            for (int i = 0; i < filePaths.Count; i++)
            {
                if (cts.IsCancellationRequested) break;

                string path = filePaths[i];
                var newJob = new Job(_app.FFProbePath);
                await newJob.AddSourceFilesAsync(new List<string> { path });
                _app.Jobs[nextId] = newJob;
                nextId++;
            }
        }
        finally
        {
            cts.Cancel();
            if (isWindowShown) GLib.Functions.IdleAdd(0, () => { progWin?.Destroy(); return false; });

            // Refresh the UI ListBox
            _refreshJobListBox();
        }
    }

    private bool _handleCloseRequest(Window sender, EventArgs e)
    {
        if (!_runner.IsRunning) return false; // Allow close

        var alert = new AlertDialog
        {
            Message = "Jobs are still running!",
            Detail = "Closing the application will immediately terminate all active FFmpeg processes. Proceed?"
        };
        alert.SetButtons(new string[] { "Cancel", "Terminate and Exit" });
        alert.SetCancelButton(0);
        alert.SetDefaultButton(1);

        // We can't await in a bool-returning event, so we use the response callback
        alert.ChooseAsync(this).ContinueWith(t =>
        {
            if (t.Result == 1)
            {
                _runner.Stop(force: true);
                GLib.Functions.IdleAdd(0, () => { this.Destroy(); return false; });
            }
        });

        return true; // Stop the immediate close
    }

    private void _refreshRetryButtonVisibility()
    {
        // Only show if not running and there are actually failed jobs
        bool hasFailed = _app.Jobs?.Values.Any(j => j.Status == Job.JobStatus.Failed) ?? false;
        _retryFailedButton.SetVisible(hasFailed && !_runner.IsRunning);
    }

    private void _setUiLocked(bool locked)
    {
        _startButton.SetVisible(!locked);
        _stopButton.SetVisible(locked);
        _isWaitingForStop = false;
        _stopButton.IconName = "media-playback-stop-symbolic";
    }

    private void _refreshJobListBox()
    {
        GLib.Functions.IdleAdd(GLib.Constants.PRIORITY_DEFAULT, () =>
        {
            // Clear existing UI rows
            var child = _jobListBox.GetFirstChild();
            while (child != null)
            {
                var next = child.GetNextSibling();
                _jobListBox.Remove(child);
                child = next;
            }

            // Clear our controller mapping
            _jobRows.Clear();

            if (_app.Jobs == null) return false;

            // Rebuild list based on sorted IDs
            var sortedKeys = _app.Jobs.Keys.OrderBy(k => k);
            foreach (var key in sortedKeys)
            {
                var job = _app.Jobs[key];
                var rowController = new JobRow(_app, this, key, job);

                _jobListBox.Append(rowController.Widget);
                _jobRows[key] = rowController; // Store the controller
            }

            return false;
        });
    }

    /// <summary>
    /// Finds the JobRow controller for a given job ID.
    /// </summary>
    private JobRow? _findRowById(int id)
    {
        return _jobRows.GetValueOrDefault(id);
    }

    /// <summary>
    /// Refreshes a specific row's UI labels on the main thread.
    /// </summary>
    public void _refreshJobRow(int id)
    {
        var row = _findRowById(id);
        if (row != null)
        {
            // Make sure UI updates happen on the GTK main thread
            GLib.Functions.IdleAdd(0, () =>
            {
                row.Refresh();
                return false;
            });
        }
    }

    public async Task RemoveSelectedJobsAsync()
    {
        var jobsToRemove = GetSelectedJobEntries();

        // Build the display string for the alert
        string itemNames;
        if (jobsToRemove.Count <= 10)
        {
            itemNames = string.Join("\n", jobsToRemove.Select(j => $"• {j.Job.Name}"));
        }
        else
        {
            // Truncate if there are too many items
            var firstFew = jobsToRemove.Take(10).Select(j => $"• {j.Job.Name}");
            itemNames = string.Join("\n", firstFew) + $"\n... and {jobsToRemove.Count - 10} more.";
        }

        var alert = new AlertDialog
        {
            Message = jobsToRemove.Count > 1 ? "Remove Selected Jobs?" : "Remove Job?",
            Detail = $"Are you sure you want to remove the following:\n\n{itemNames}"
        };

        alert.SetButtons(new string[] { "Cancel", "Remove" });
        alert.SetCancelButton(0);
        alert.SetDefaultButton(1);

        try
        {
            int response = await alert.ChooseAsync(this);

            if (response == 1) // User clicked "Remove"
            {
                foreach (var item in jobsToRemove)
                {
                    _app.Jobs.Remove(item.Id);
                }

                _refreshJobListBox();
            }
        }
        catch (Exception ex)
        {
            Console.WriteLine($"Removal error: {ex.Message}");
        }
    }

    public async Task AddClonedJob(Job job)
    {
        int nextId = (_app.Jobs.Count == 0) ? 1 : _app.Jobs.Keys.Max() + 1;
        _app.Jobs.Add(nextId, job);
        _refreshJobListBox();
    }

    public async Task ResetJobStatus()
    {
        var jobs = GetSelectedJobEntries();
        foreach ((int id, Job job) in jobs)
            job.Status = Job.JobStatus.Pending;
        _refreshJobListBox();
    }

    public void BatchToggleStreams(string streamType)
    {
        var entries = GetSelectedJobEntries();
        if (entries.Count == 0) return;

        foreach (var entry in entries)
        {
            foreach (var source in entry.Job.Sources)
            {
                foreach (var stream in source.Streams)
                {
                    if (stream.Type.Equals(streamType, StringComparison.OrdinalIgnoreCase))
                    {
                        stream.Active = !stream.Active;
                    }
                }
            }
        }
        _refreshJobListBox();
    }

    public void BatchApplyTemplate(string streamType)
    {
        var entries = GetSelectedJobEntries();
        if (entries.Count == 0) return;

        // Open TemplateManager in Picker Mode
        var picker = new TemplateManagerWindow(_app, this, true, typeof(TranscodingTemplate).FullName!, streamType, (template) =>
        {
            foreach (var entry in entries)
            {
                foreach (var source in entry.Job.Sources)
                {
                    foreach (var stream in source.Streams)
                    {
                        if (stream.Type.Equals(streamType, StringComparison.OrdinalIgnoreCase))
                        {
                            stream.Template = template.Name;
                            // Clone the encoder settings from the template to the stream
                            if (template is TranscodingTemplate tt)
                            {
                                stream.EncoderSettings = tt.EncoderSettings;
                            }
                        }
                    }
                }
            }
            _refreshJobListBox();
        });
        picker.Present();
    }

    public void BatchChangeOutputDirectory()
    {
        var entries = GetSelectedJobEntries();
        if (entries.Count == 0) return;

        var chooser = FileChooserNative.New(
            "Select Batch Output Directory",
            this,
            FileChooserAction.SelectFolder,
            "Select",
            "Cancel"
        );

        chooser.OnResponse += (s, e) =>
        {
            if (e.ResponseId == (int)ResponseType.Accept)
            {
                string? path = chooser.GetFile()?.GetPath();
                if (!string.IsNullOrEmpty(path))
                {
                    foreach (var entry in entries)
                    {
                        entry.Job.OutputDirectory = path;
                    }
                    _refreshJobListBox();
                }
            }
            chooser.Destroy();
        };
        chooser.Show();
    }

    public void BatchChangeContainer()
    {
        var entries = GetSelectedJobEntries();
        if (entries.Count == 0) return;

        var picker = new TemplateManagerWindow(_app, this, true, typeof(ContainerTemplate).FullName!, "", (template) =>
        {
            if (template is ContainerTemplate ct)
            {
                foreach (var entry in entries)
                {
                    entry.Job.Multiplexer = ct.Muxer;
                    entry.Job.MuxerParameters = new Dictionary<string, object>(ct.Parameters);
                }
                _refreshJobListBox();
            }
        });
        picker.Present();
    }

    public void SetParallelGroup()
    {
        var entries = GetSelectedJobEntries();
        if (entries.Count == 0) return;

        // Determine maximum group number currently used
        byte maxGroup = 0;
        foreach (var (_, job) in _app.Jobs)
            if (job.ParallelGroup > maxGroup)
                maxGroup = job.ParallelGroup;
        maxGroup++;

        // Simple input dialog using a Window
        var dialog = new Window { Title = "Set Parallel processing group", Modal = true, TransientFor = this };
        dialog.SetParent(this);
        dialog.SetDefaultSize(320, 100);
        dialog.SetResizable(false);
        dialog.SetModal(true);

        var box = new Box { Spacing = 16, MarginTop = 16, MarginBottom = 16, MarginStart = 16, MarginEnd = 16 };
        box.SetOrientation(Orientation.Vertical);

        var updateGroup = (byte value) =>
        {
            foreach (var entry in entries)
                entry.Job.ParallelGroup = value;
            _refreshJobListBox();
        };

        var spin = SpinButton.New(Adjustment.New(maxGroup, 1, 255, 1, 10, 0), 1, 0);
        spin.Numeric = true;

        var btnBox = new Box { Spacing = 6, Halign = Align.End };
        var btnCancel = new Button { Label = "Cancel" };
        btnCancel.OnClicked += (s, e) => dialog.Close();

        var btnSave = new Button { Label = "Apply" };
        btnSave.AddCssClass("suggested-action");
        btnSave.OnClicked += (s, e) =>
        {
            updateGroup((byte)spin.Value);
            dialog.Close();
        };

        var btnReset = new Button { Label = "No group" };
        btnReset.OnClicked += (s, e) =>
        {
            updateGroup(0);
            dialog.Close();
        };

        btnBox.Append(btnCancel);
        btnBox.Append(btnReset);
        btnBox.Append(btnSave);

        box.Append(new Label { Label_ = "Parallel processing group number (1 - 255):", Xalign = 0 });
        box.Append(spin);
        box.Append(btnBox);

        dialog.SetChild(box);
        dialog.Present();
    }


    // Helpers
    private List<(int Id, Job Job)> GetSelectedJobEntries()
    {
        var selectedIndices = new List<int>();
        _jobListBox.SelectedForeach((_, row) => selectedIndices.Add(row.GetIndex()));

        var sortedKeys = _app.Jobs.Keys.OrderBy(k => k).ToList();
        return selectedIndices
            .Where(idx => idx >= 0 && idx < sortedKeys.Count)
            .Select(idx => (Id: sortedKeys[idx], Job: _app.Jobs[sortedKeys[idx]]))
            .ToList();
    }

    private void ScrollToJob(int id)
    {
        // Run on Idle to ensure the UI has finished updating layout from the status change
        GLib.Functions.IdleAdd(0, () =>
        {
            if (_jobRows.TryGetValue(id, out var row))
            {
                var widget = row.Widget;

                // Compute the position of the row relative to the ListBox
                if (widget.ComputeBounds(_jobListBox, out var bounds))
                {
                    var adjustment = _jobListBoxScroller.Vadjustment;
                    if (adjustment is not null)
                    {
                        double rowY = bounds.GetY();
                        double rowHeight = bounds.GetHeight();
                        double viewHeight = adjustment.PageSize;
                        double currentScroll = adjustment.Value;

                        // Logic: 
                        // - If row is above the view, scroll up to it.
                        // - If row is below the view, scroll down to it.
                        // - Optional: We scroll so the row is slightly centered or at the top.

                        if (rowY < currentScroll || (rowY + rowHeight) > (currentScroll + viewHeight))
                            adjustment.Value = rowY; // Scroll to put the row at the top
                    }
                }
            }
            return false;
        });
    }
}
