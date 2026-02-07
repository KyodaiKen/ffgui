namespace FFGui.UI;

using Gtk;
using FFGui.Models;
using FFGui.Core;

public class FilterParameterEditor : Window
{
    private readonly EncoderSettings.FilterSettings _settings;
    private readonly FFmpegFilter _schema;
    private readonly Action _onSave;
    private readonly ListBox _listParams;
    private readonly Dictionary<string, Widget> _activeWidgets = new();

    private readonly FFGuiApp _app;

    public FilterParameterEditor(FFGuiApp app, Window parent, EncoderSettings.FilterSettings settings, FFmpegFilter schema, Action onSave)
    {
        _app = app;
        _settings = settings;
        _schema = schema;
        _onSave = onSave;

        SetTitle($"Configure Filter: {settings.FilterName}");
        SetTransientFor(parent);
        SetModal(true);
        SetDefaultSize(500, 400);

        var mainBox = new Box { Spacing = 12, MarginStart = 12, MarginEnd = 12, MarginTop = 12, MarginBottom = 12 };
        mainBox.SetOrientation(Orientation.Vertical);
        SetChild(mainBox);

        // Header
        var header = new Box();
        header.SetOrientation(Orientation.Horizontal);
        header.Append(new Label { Label_ = "<b>Active Parameters</b>", UseMarkup = true, Xalign = 0, Hexpand = true });

        var btnAdd = new Button { Label = "Add Parameter", IconName = "list-add-symbolic" };
        btnAdd.AddCssClass("pill");
        btnAdd.OnClicked += OnAddParamClicked;
        header.Append(btnAdd);
        mainBox.Append(header);

        // Parameter List
        var scroll = new ScrolledWindow { Vexpand = true, HasFrame = true };
        _listParams = new ListBox { SelectionMode = SelectionMode.None };
        _listParams.AddCssClass("boxed-list");
        scroll.SetChild(_listParams);
        mainBox.Append(scroll);

        // Footer
        var btnApply = new Button { Label = "Apply Changes" };
        btnApply.AddCssClass("suggested-action");
        btnApply.SetHalign(Align.End);
        btnApply.OnClicked += (s, e) =>
        {
            _saveParameters();
            _onSave();
            this.Close();
        };
        mainBox.Append(btnApply);

        // Initial Load
        foreach (var param in _settings.Parameters)
        {
            if (_schema.Parameters.TryGetValue(param.Key, out var pSchema))
                _addParamRow(param.Key, param.Value, pSchema);
        }
    }

    private void OnAddParamClicked(object? sender, EventArgs e)
    {
        // Use PickerWindow to find parameters available for THIS filter
        var picker = new PickerWindow(_app.Cache, PickerType.Parameter, (obj) =>
        {
            if (obj is PickerWindow.PickerResult res && res.Data is FFmpegParameter pSchema)
                _addParamRow(res.Key, pSchema.Default, pSchema);
        }, contextData: _schema);

        picker.SetTransientFor(this);
        picker.Present();
    }

    private void _addParamRow(string name, object? value, FFmpegParameter schema)
    {
        if (_activeWidgets.ContainsKey(name)) return;

        var box = new Box { Spacing = 10, MarginStart = 6, MarginEnd = 6, MarginTop = 4, MarginBottom = 4 };
        box.SetOrientation(Orientation.Horizontal);
        box.Append(new Label { Label_ = name, Xalign = 0, WidthRequest = 100 });

        // Build the appropriate input widget using our factory
        var valWidget = ParameterRowFactory.BuildValueWidget(name, value, schema, () => { });
        valWidget.Hexpand = true;
        box.Append(valWidget);

        var btnDel = Button.NewFromIconName("user-trash-symbolic");
        box.Append(btnDel);

        var row = new ListBoxRow { Child = box };
        btnDel.OnClicked += (s, e) =>
        {
            _listParams.Remove(row);
            _activeWidgets.Remove(name);
        };

        _activeWidgets[name] = valWidget;
        _listParams.Append(row);
    }

    private void _saveParameters()
    {
        _settings.Parameters.Clear();
        foreach (var entry in _activeWidgets)
        {
            var val = ParameterRowFactory.ExtractWidgetValue(entry.Value, _schema.Parameters[entry.Key]);
            if (val != null) _settings.Parameters[entry.Key] = val;
        }
    }
}