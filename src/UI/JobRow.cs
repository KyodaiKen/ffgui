namespace FFGui.UI;

using Gtk;
using Gio;
using Gdk;
using System;

using FFGui.Core;
using FFGui.Models;

public class JobRow
{
    public ListBoxRow Widget { get; private set; }
    public Job JobData { get; private set; }
    public int JobId { get; private set; }

    private FFGuiApp _app;
    private Label _lblTitle;
    private Label _lblInfo;
    private Image _imgStatus;
    private Label _lblPGroup;
    private ProgressBar _progressBar;
    private Label _lblStatusInfo;
    private PopoverMenu _popover;
    private SimpleActionGroup _actionGroup;

    private readonly Window _parent;
    public JobRow(FFGuiApp app, Window parent, int id, Job job)
    {
        _app = app;
        _parent = parent;
        JobData = job;
        JobId = id;
        Widget = new ListBoxRow();


        var vbox = new Box { Spacing = 4 };
        vbox.SetOrientation(Orientation.Vertical);
        vbox.SetMarginBottom(6); vbox.SetMarginTop(6);
        vbox.SetMarginStart(10); vbox.SetMarginEnd(10);
        Widget.SetChild(vbox);

        var grid = new Grid() { ColumnSpacing = 12, RowSpacing = 4 };

        // ROW1: HEADER
        // Status icon
        _imgStatus = new Image { };
        _lblTitle = new Label { Halign = Align.Start, Hexpand = true, UseMarkup = true, Ellipsize = Pango.EllipsizeMode.Middle };
        _lblInfo = new Label { Halign = Align.Start, CssClasses = ["job-lbl-info"] };

        grid.Attach(_imgStatus, 0, 0, 1, 1);
        grid.Attach(_lblTitle, 1, 0, 1, 1);
        grid.Attach(_lblInfo, 2, 0, 1, 1);

        // ROW2: PARALLEL GROUP NUMBER AND PROGRESS BAR
        _lblPGroup = new Label() { CssClasses = ["job-lbl-info"] };
        _progressBar = new ProgressBar { Hexpand = true, ShowText = false };
        grid.Attach(_lblPGroup, 0, 1, 1, 1);
        grid.Attach(_progressBar, 1, 1, 2, 1);

        //ROW3: STATUS INFO
        _lblStatusInfo = new() { Halign = Align.Start, CssClasses = ["job-lbl-status-info"] };
        grid.Attach(_lblStatusInfo, 1, 2, 2, 1);
        vbox.Append(grid);

        // Context Menu Setup
        var builder = Builder.NewFromString(FFGui.UI.Menus.JobListWindowContextMenu, -1);
        var menuModel = builder.GetObject("context-menu") as MenuModel ?? throw new Exception("Menu model not found");

        _actionGroup = SimpleActionGroup.New();

        // Add basic actions (Mapping to your Python names)
        AddAction("job_setup", (a, p) => _onJobEdit());
        AddAction("remove_job", (a, p) => _onJobRemove());
        AddAction("job_clone", (a, p) => _onJobClone());
        AddAction("reset_job_status", (a, p) => _onResetJobStatus());

        var listWindow = _parent as JobListWindow;
        AddAction("toggle_video", (a, v) => listWindow?.BatchToggleStreams("video"));
        AddAction("toggle_audio", (a, v) => listWindow?.BatchToggleStreams("audio"));
        AddAction("toggle_subtitles", (a, v) => listWindow?.BatchToggleStreams("subtitle"));

        AddAction("batch_tpl_video", (a, v) => listWindow?.BatchApplyTemplate("video"));
        AddAction("batch_tpl_audio", (a, v) => listWindow?.BatchApplyTemplate("audio"));
        AddAction("batch_tpl_subtitle", (a, v) => listWindow?.BatchApplyTemplate("subtitle"));

        AddAction("batch_container", (a, v) => listWindow?.BatchChangeContainer());
        AddAction("batch_chg_out_dir", (a, v) => listWindow?.BatchChangeOutputDirectory());

        AddAction("set_parallel_group", (a, v) => listWindow?.SetParallelGroup());

        Widget.InsertActionGroup("context", _actionGroup);

        _popover = PopoverMenu.NewFromModel(menuModel);
        _popover.SetParent(Widget);
        _popover.SetHasArrow(false);

        // Right-click Gesture
        var gesture = GestureClick.New();
        gesture.SetButton(3);
        gesture.OnPressed += (s, e) =>
        {
            // Select row if not selected
            if (Widget.GetParent() is ListBox listbox)
            {
                if (!Widget.IsSelected()) listbox.SelectRow(Widget);
            }

            _popover.SetPointingTo(new Rectangle { X = (int)e.X, Y = (int)e.Y, Width = 1, Height = 1 });
            _popover.Popup();
        };
        Widget.AddController(gesture);

        _lblTitle.SetMarkup($"<b>{JobData.Name}</b>");

        _setInfoLabel();

        UpdateUI();
    }

    /// <summary>
    /// Refreshes the static labels and metadata of the row.
    /// </summary>
    public void Refresh()
    {
        _lblTitle.SetMarkup($"<b>{JobData.Name}</b>");
        _setInfoLabel();
        UpdateUI();
    }

    private void _setInfoLabel()
    {
        int fileCount = JobData.Sources.Count;
        string fileText = fileCount == 1 ? "File" : "Files";

        int activeStreamCount = JobData.Sources.Sum(s => s.Streams.Count(st => st.Active));
        string streamText = activeStreamCount == 1 ? "Stream" : "Streams";

        _lblInfo.SetText($"{fileCount} {fileText}, {activeStreamCount} {streamText}, {TimeSpan.FromSeconds(JobData.TotalDuration):hh\\:mm\\:ss\\.fff}");
    }

    private void AddAction(string name, Action<SimpleAction, GLib.Variant?> callback)
    {
        var act = SimpleAction.New(name, null);
        act.OnActivate += (s, e) => callback(s, e.Parameter);
        _actionGroup.AddAction(act);
    }

    public void UpdateUI(string progressInfo = "", double progress = 0)
    {
        _lblStatusInfo.SetText(progressInfo);
        if (JobData.ParallelGroup > 0)
            _lblPGroup.SetText(JobData.ParallelGroup.ToString());
        else
            _lblPGroup.SetText("");
        _progressBar.SetFraction(progress);

        // Handle Status Icon
        switch (JobData.Status)
        {
            case Job.JobStatus.Pending:
                _imgStatus.SetFromIconName("alarm-symbolic");
                _imgStatus.SetVisible(true);
                break;

            case Job.JobStatus.Running:
                _imgStatus.SetFromIconName("process-working-symbolic");
                _imgStatus.SetVisible(true);
                break;

            case Job.JobStatus.Successful:
                _imgStatus.SetFromIconName("emblem-ok-symbolic");
                _imgStatus.SetVisible(true);
                break;

            case Job.JobStatus.Failed:
                _imgStatus.SetFromIconName("dialog-error-symbolic");
                _imgStatus.SetVisible(true);
                break;
        }

        // Enable/Disable the view_error action
        var errorAction = _actionGroup.LookupAction("view_error") as SimpleAction;
        errorAction?.SetEnabled(JobData.Status == Job.JobStatus.Failed);
    }

    // --- EVENTS ---

    private void _onJobEdit()
    {
        var editor = new JobEditorWindow(_app, EditorMode.Edit, JobData, (confirmedJob) =>
        {
            _lblTitle.SetMarkup($"<b>{confirmedJob.Name}</b>");
            _setInfoLabel();
        });
        editor.Present();
    }

    private async void _onJobRemove()
    {
        // Find the parent window
        var root = Widget.GetRoot();
        if (root is not JobListWindow listWindow) return;

        await listWindow.RemoveSelectedJobsAsync();
    }

    private void _onJobClone()
    {
        var editor = new JobEditorWindow(_app, EditorMode.Edit, JobData.Clone(), async (confirmedJob) =>
        {
            var root = Widget.GetRoot();
            if (root is not JobListWindow listWindow) return;

            await listWindow.AddClonedJob(confirmedJob);
        });
        editor.Present();
    }

    private void _onResetJobStatus() => (_parent as JobListWindow)?.ResetJobStatus();

    private void _onViewError()
    {
        var logWindow = new Window
        {
            Title = $"Error Log: {JobData.Name}",
            TransientFor = _parent,
            Modal = true,
            DefaultWidth = 800,
            DefaultHeight = 500
        };

        var scrolled = new ScrolledWindow { MarginBottom = 12, MarginEnd = 12, MarginStart = 12, MarginTop = 12 };
        scrolled.SetPolicy(PolicyType.Automatic, PolicyType.Automatic);

        var textView = new TextView
        {
            Editable = false,
            CursorVisible = false,
            WrapMode = WrapMode.None,
            Monospace = true // Crucial for log readability
        };

        var err_info = string.IsNullOrEmpty(JobData.ErrorLog) ? "No log data available." : JobData.ErrorLog;
        textView.GetBuffer().SetText(err_info, err_info.Length);

        scrolled.SetChild(textView);
        logWindow.SetChild(scrolled);
        logWindow.Present();
    }
}
