namespace FFGui.UI;

using Gtk;
using FFGui.Models;
using System.Text;
using FFGui.Core;

public class TemplateEditorWindow : Window
{
    private readonly FFGuiApp _app;
    private readonly Template _template;
    private readonly EditorMode _mode;
    private readonly Action<Template, string>? _onSave;

    private Entry _entFileName = null!;
    private TextView _txtDescription = null!;
    private DropDown _ddType = null!;

    private Dictionary<string, object> _factoryWidgets = new();

    public TemplateEditorWindow(FFGuiApp app, Template template, EditorMode mode, Action<Template, string>? onSave = null)
    {
        _app = app;
        _template = template;
        _mode = mode;
        _onSave = onSave;

        SetTitle(_mode == EditorMode.New ? "Create Template" : "Edit Template");
        SetDefaultSize(500, 600);
        SetModal(true);

        BuildUI();

        _populateTemplateData();
    }

    private void BuildUI()
    {
        var mainBox = new Box { Spacing = 12 };
        mainBox.SetOrientation(Orientation.Vertical);
        mainBox.SetMarginStart(12);
        mainBox.SetMarginEnd(12);
        mainBox.SetMarginTop(12);
        mainBox.SetMarginBottom(12);

        var grid = new Grid { ColumnSpacing = 10, RowSpacing = 12 };

        // Row 0: Template Name
        grid.Attach(new Label { Label_ = "Template Name:", Xalign = 0 }, 0, 0, 1, 1);
        _entFileName = new Entry { Text_ = _template.Name, Hexpand = true };
        grid.Attach(_entFileName, 1, 0, 1, 1);

        grid.Attach(new Label { Label_ = "Description:", Xalign = 0, Yalign = 0 }, 0, 1, 1, 1);

        var scrollDesc = new ScrolledWindow
        {
            MinContentHeight = 100,
            HasFrame = true,
            Hexpand = true
        };

        _txtDescription = new TextView
        {
            WrapMode = WrapMode.Word,
            AcceptsTab = false,
            LeftMargin = 10,
            RightMargin = 10,
            TopMargin = 10,
            BottomMargin = 10
        };
        
        _txtDescription.Buffer?.Text = _template.Description;

        scrollDesc.SetChild(_txtDescription);
        grid.Attach(scrollDesc, 1, 1, 1, 1);

        // Only show type if needed. Container formats do not need the type.
        if (_template is TranscodingTemplate || _template is FilterTemplate)
        {
            grid.Attach(new Label { Label_ = "Template Type:", Xalign = 0 }, 0, 2, 1, 1);

            // Create the dropdown items
            var typeList = StringList.New(["Video", "Audio", "Subtitle"]);
            _ddType = new DropDown { Model = typeList, Hexpand = true };

            // Set initial selection based on existing template type
            if (_template is TranscodingTemplate ttts)
            {
                uint index = ttts.Type.ToLower() switch
                {
                    "audio" => 1,
                    "subtitle" => 2,
                    _ => 0
                };
                _ddType.SetSelected(index);
            }
            grid.Attach(_ddType, 1, 2, 1, 1);
        }

        // Separator
        var sep = new Separator { MarginTop = 6, MarginBottom = 6 };
        sep.SetOrientation(Orientation.Horizontal);
        grid.Attach(sep, 0, 3, 2, 1);


        // Row 3: Factory Content (Dynamic)
        Widget factoryContent;
        _factoryWidgets.Clear();

        if (_template is TranscodingTemplate tt)
        {
            var notebook = new Notebook
            {
                Hexpand = true,
                Vexpand = true
            };

            // Page 1: Transcoding
            var pageTranscoding = JobEditorUiFactory.BuildEncoderSetup(tt.EncoderSettings, out var widgetsEnc);
            foreach (var kvp in widgetsEnc) _factoryWidgets[kvp.Key] = kvp.Value; // Merge
            notebook.AppendPage(pageTranscoding, new Label { Label_ = "Transcoding" });

            // Page 2: Filters
            // Assuming EncoderSettings has a ComplexFilter boolean
            var pageFilters = JobEditorUiFactory.BuildFilterSetup(tt.EncoderSettings.UsesComplexFilters, out var widgetsFilt);
            foreach (var kvp in widgetsFilt) _factoryWidgets[kvp.Key] = kvp.Value; // Merge
            notebook.AppendPage(pageFilters, new Label { Label_ = "Filters" });

            factoryContent = notebook;
        }
        else if (_template is ContainerTemplate ct)
        {
            factoryContent = JobEditorUiFactory.BuildContainerSetupBox(ct.Muxer, ct.Parameters, out var widgets);
            foreach (var kvp in widgets) _factoryWidgets[kvp.Key] = kvp.Value;
        }
        else if (_template is FilterTemplate ft)
        {
            factoryContent = JobEditorUiFactory.BuildFilterSetup(ft.ComplexFilters, out var widgets);
            foreach (var kvp in widgets) _factoryWidgets[kvp.Key] = kvp.Value;
        }
        else
        {
            factoryContent = new Label { Label_ = "Unknown Template Type" };
        }

        factoryContent.Vexpand = true;
        grid.Attach(factoryContent, 0, 4, 2, 1);

        mainBox.Append(grid);

        // Footer: Action Buttons
        var actionBox = new Box { Spacing = 6, Halign = Align.End };
        actionBox.SetOrientation(Orientation.Horizontal);

        var btnCancel = new Button { Label = "Cancel" };
        btnCancel.OnClicked += (s, e) => Close();

        var btnOk = new Button { Label = _mode == EditorMode.New ? "Create" : "Apply" };
        btnOk.AddCssClass("suggested-action");
        btnOk.OnClicked += _onOkClicked;

        actionBox.Append(btnCancel);
        actionBox.Append(btnOk);

        // Register the events for the factory-built widgets
        _registerFactoryEvents();

        mainBox.Append(actionBox);

        SetChild(mainBox);

        _connectTemplateButtons();
    }

    private void _onOkClicked(object? sender, EventArgs e)
    {
        _syncUiToTemplate();

        // Validate Template Name
        if (string.IsNullOrWhiteSpace(_template.Name))
        {
            _showWarning("Template Name cannot be empty.");
            return;
        }

        _onSave?.Invoke(_template, _template.Name);
        Close();
    }

    private void _populateFilterUiCommon(bool isComplex, List<EncoderSettings.FilterSettings> filters)
    {
        // Set DropDown Mode
        if (_factoryWidgets.TryGetValue("ddFilterMode", out var ddObj) && ddObj is DropDown dd)
            dd.Selected = isComplex ? 1u : 0u;

        // Populate ListBox
        if (_factoryWidgets.TryGetValue("listSimpleFilters", out var lbObj) && lbObj is ListBox lbFilters)
        {
            _clearListBox(lbFilters);
            foreach (var filter in filters ?? [])
            {
                var row = JobEditorUiFactory.CreateFilterRow(
                    filter,
                    onRemove: lbFilters.Remove,
                    onEdit: () => _openFilterEditor(filter)
                );
                lbFilters.Append(row);
            }
        }
    }

    private void _populateTemplateData()
    {
        // Populate Encoder Parameters List
        if (_template is TranscodingTemplate tt)
        {
            // --- Transcoding Params (Existing) ---
            if (_factoryWidgets.TryGetValue("entEncoder", out var entObj) && entObj is Entry entEncoder)
                entEncoder.SetText(tt.EncoderSettings.Encoder);

            if (_factoryWidgets.TryGetValue("lbESEncoderParams", out var lbObj) && lbObj is ListBox lbParams)
            {
                _clearListBox(lbParams);
                FFmpegCodec? encoderSchema = null;
                if (!string.IsNullOrEmpty(tt.EncoderSettings.Encoder))
                    _app.Cache.Codecs.TryGetValue(tt.EncoderSettings.Encoder, out encoderSchema);

                foreach (var param in tt.EncoderSettings.Parameters ?? [])
                {
                    FFmpegParameter? paramSchema = null;
                    encoderSchema?.Parameters.TryGetValue(param.Key, out paramSchema);
                    var row = ParameterRowFactory.CreateParameterRow(
                        key: param.Key, value: param.Value, schema: paramSchema,
                        onRemove: lbParams.Remove, onChanged: null
                    );
                    lbParams.Append(row);
                }
            }

            // --- Filter Params (New for Transcoding) ---
            // Make sure EncoderSettings.Filters is initialized
            tt.EncoderSettings.Filters ??= [];
            _populateFilterUiCommon(tt.EncoderSettings.UsesComplexFilters, tt.EncoderSettings.Filters);
        }
        else if (_template is FilterTemplate ft)
        {
            _populateFilterUiCommon(ft.ComplexFilters, ft.Filters);
        }
        // Populate Container parameters
        else if (_template is ContainerTemplate ct)
        {
            // Set the DropDown mode (0 = Simple, 1 = Complex)
            if (_factoryWidgets.TryGetValue("entCSContainerFormat", out var entObj) && entObj is Entry ent)
                ent.Text_ = ct.Muxer;

            // Populate the Container parameters
            if (_factoryWidgets.TryGetValue("lbCSMuxerParams", out var lbObj) && lbObj is ListBox lbContainerParms)
            {
                while (lbContainerParms.GetFirstChild() is Widget child) lbContainerParms.Remove(child);

                foreach (var parm in ct.Parameters ?? [])
                {
                    var row = ParameterRowFactory.CreateParameterRow(
                        key: parm.Key,
                        value: parm.Value,
                        schema: _app.Cache.Formats[ct.Muxer].Parameters[parm.Key],
                        onRemove: lbContainerParms.Remove,
                        onChanged: () => { }
                    );
                    lbContainerParms.Append(row);
                    row.Show();
                }
            }
        }
    }

    private void _syncParamsToTemplate()
    {
        // Handle Filter Logic (Shared)
        // We check if the UI elements exist, which implies we are on a page that supports filters
        if (_factoryWidgets.ContainsKey("listSimpleFilters"))
        {
            bool complexMode = false;
            if (_factoryWidgets.TryGetValue("ddFilterMode", out var ddObj) && ddObj is DropDown dd)
                complexMode = dd.Selected == 1;

            List<EncoderSettings.FilterSettings>? targetFilters = null;

            // SWITCH: Determine where to put the filters
            if (_template is FilterTemplate ft)
            {
                ft.ComplexFilters = complexMode;
                targetFilters = ft.Filters;
            }
            else if (_template is TranscodingTemplate tt)
            {
                tt.EncoderSettings.UsesComplexFilters = complexMode;
                tt.EncoderSettings.Filters ??= new();
                targetFilters = tt.EncoderSettings.Filters;
            }

            // Sync the list if valid target found
            if (targetFilters != null && _factoryWidgets.TryGetValue("listSimpleFilters", out var lbObj) && lbObj is ListBox lbFilters)
            {
                targetFilters.Clear();
                var child = lbFilters.GetFirstChild();
                while (child != null)
                {
                    // Use unboxing helper or direct check
                    var row = child as JobEditorUiFactory.FilterRow
                           ?? (child as ListBoxRow)?.GetChild() as JobEditorUiFactory.FilterRow;

                    if (row != null) targetFilters.Add(row.Settings);

                    child = child.GetNextSibling();
                }
            }
        }

        // Handle Parameters Logic (Transcoding & Container)
        // (This part remains largely the same, just make sure it runs for TranscodingTemplate)
        if (_template is TranscodingTemplate ttParams)
        {
            // Sync Encoder Params
            if (_factoryWidgets.TryGetValue("lbESEncoderParams", out var lbObj) && lbObj is ListBox lbParams)
            {
                ttParams.EncoderSettings.Parameters ??= [];
                var targetDict = ttParams.EncoderSettings.Parameters;
                targetDict.Clear();

                var child = lbParams.GetFirstChild();
                while (child != null)
                {
                    // Unboxing
                    var row = child as ParameterRow ?? (child as ListBoxRow)?.GetChild() as ParameterRow;
                    if (row != null)
                    {
                        var val = ParameterRowFactory.ExtractWidgetValue(row.ValueWidget, row.Schema);
                        if (val != null) targetDict[row.Key] = val;
                    }
                    child = child.GetNextSibling();
                }
            }
        }
        else if (_template is ContainerTemplate ct)
        {
            // Sync Container Params (Keep existing logic)
            if (_factoryWidgets.TryGetValue("lbCSMuxerParams", out var lbObj) && lbObj is ListBox lbParams)
            {
                ct.Parameters ??= [];
                ct.Parameters.Clear();
                // ... (Same loop pattern as above) ...
                var child = lbParams.GetFirstChild();
                while (child != null)
                {
                    var row = child as ParameterRow ?? (child as ListBoxRow)?.GetChild() as ParameterRow;
                    if (row != null)
                    {
                        var val = ParameterRowFactory.ExtractWidgetValue(row.ValueWidget, row.Schema);
                        if (val != null) ct.Parameters[row.Key] = val;
                    }
                    child = child.GetNextSibling();
                }
            }
        }
    }

    private void _registerFactoryEvents()
    {
        // --- Encoder Template Events ---
        if (_factoryWidgets.TryGetValue("btnESPickEncoder", out var btnEP))
        {
            ((Button)btnEP).OnClicked += (s, e) =>
            {
                _syncUiToTemplate();
                var streamType = (_template as TranscodingTemplate)?.Type ?? "Video";
                var picker = new PickerWindow(_app.Cache, PickerType.Encoder, (obj) =>
                {
                    if (obj is PickerWindow.PickerResult result && _template is TranscodingTemplate tt)
                    {
                        tt.EncoderSettings.Encoder = result.Key; // Key is the codec name
                        if (_factoryWidgets.TryGetValue("entEncoder", out var ent))
                            ((Entry)ent).SetText(result.Key);
                    }
                }, streamType: streamType);
                picker.SetTransientFor(this);
                picker.Present();
            };
        }

        if (_factoryWidgets.TryGetValue("btnESAddParam", out var btnEAdd))
            ((Button)btnEAdd).OnClicked += (s, e) => _openParamPicker();

        // --- Container Template Events ---
        if (_factoryWidgets.TryGetValue("btnCSSelectContainer", out var btnCP))
        {
            ((Button)btnCP).OnClicked += (s, e) =>
            {
                _syncUiToTemplate();
                var picker = new PickerWindow(_app.Cache, PickerType.Muxer, (obj) =>
                {
                    if (obj is PickerWindow.PickerResult result && _template is ContainerTemplate ct)
                    {
                        ct.Muxer = result.Key; // Key is the format name
                        if (_factoryWidgets.TryGetValue("entCSContainerFormat", out var ent))
                            ((Entry)ent).SetText(result.Key);
                    }
                });
                picker.SetTransientFor(this);
                picker.Present();
            };
        }

        if (_factoryWidgets.TryGetValue("btnCSAddMuxParam", out var btnCAdd))
            ((Button)btnCAdd).OnClicked += (s, e) => _openParamPicker();

        // --- Filter Events (Shared) ---
        if (_factoryWidgets.TryGetValue("btnFSAddFilter", out var btnFAdd))
        {
            ((Button)btnFAdd).OnClicked += (s, e) =>
            {
                _syncUiToTemplate();
                var picker = new PickerWindow(_app.Cache, PickerType.Filter, (obj) =>
                {
                    if (obj is PickerWindow.PickerResult result)
                    {
                        var newFilter = new EncoderSettings.FilterSettings { FilterName = result.Key };

                        // SWITCH: Add to correct model and refresh UI
                        if (_template is FilterTemplate ft)
                        {
                            ft.Filters.Add(newFilter);
                            _populateFilterUiCommon(ft.ComplexFilters, ft.Filters);
                        }
                        else if (_template is TranscodingTemplate tt)
                        {
                            tt.EncoderSettings.Filters ??= new();
                            tt.EncoderSettings.Filters.Add(newFilter);
                            _populateFilterUiCommon(tt.EncoderSettings.UsesComplexFilters, tt.EncoderSettings.Filters);
                        }
                    }
                }, streamType: _template switch
                {
                    TranscodingTemplate t => t.Type,
                    FilterTemplate f => f.Type,
                    _ => throw new InvalidOperationException("Template has no Type")
                });
                picker.SetTransientFor(this);
                picker.Present();
            };
        }
    }

    private void _openParamPicker()
    {
        ListBox? lb = null;
        object? schema = null;
        string currentStreamType = "";
        _syncUiToTemplate();
        if (_template is TranscodingTemplate tt)
        {
            // Sync the type from dropdown
            var selectedItem = _ddType.GetSelectedItem() as StringObject;
            tt.Type = selectedItem?.String?.ToLower() ?? "video";
            currentStreamType = tt.Type;

            // IMPORTANT: Sync the Encoder name from the UI widget before cache lookup
            if (_factoryWidgets.TryGetValue("entEncoder", out var entObj) && entObj is Entry entEncoder)
            {
                tt.EncoderSettings.Encoder = entEncoder.GetText();
            }

            if (_factoryWidgets.TryGetValue("lbESEncoderParams", out var obj)) lb = obj as ListBox;

            // Look up the specific codec schema (e.g., libsvtav1)
            if (!string.IsNullOrEmpty(tt.EncoderSettings.Encoder) &&
                _app.Cache.Codecs.TryGetValue(tt.EncoderSettings.Encoder, out var codec))
            {
                schema = codec;
            }
        }
        else if (_template is ContainerTemplate ct)
        {
            if (_factoryWidgets.TryGetValue("lbCSMuxerParams", out var obj)) lb = obj as ListBox;
            if (_app.Cache.Formats.TryGetValue(ct.Muxer, out var format))
                schema = format;
        }
        else if (_template is FilterTemplate ft)
        {
            // Logic for Filter Templates
            currentStreamType = ft.Type?.ToLower() ?? "video";

            // Simple filters use 'listSimpleFiltersFilters', complex filters use 'lbComplexFilters'
            string lbKey = ft.ComplexFilters ? "lbComplexFilters" : "listSimpleFiltersFilters";
            if (_factoryWidgets.TryGetValue(lbKey, out var obj)) lb = obj as ListBox;

            // For Filter Templates, the 'schema' in the picker often defaults to 
            // the global filter list in the cache if a specific one isn't active
            schema = _app.Cache;
        }

        if (lb == null) return;

        // Pass currentStreamType to the picker so it filters correctly
        var picker = new PickerWindow(_app.Cache, PickerType.Parameter, (obj) =>
        {
            if (obj is PickerWindow.PickerResult res && res.Data is FFmpegParameter pSchema)
            {
                if (_checkParameterExists(lb, res.Key)) return;

                var row = ParameterRowFactory.CreateParameterRow(
                    res.Key, pSchema.Default, pSchema,
                    onRemove: (r) => lb.Remove(r),
                    onChanged: null
                );
                lb.Append(row);
            }
        }, contextData: schema, streamType: currentStreamType);

        picker.SetTransientFor(this);
        picker.Present();
    }

    private void _syncUiToTemplate()
    {
        _template.Name = _entFileName.GetText();
        _template.Description = _txtDescription.Buffer?.Text ?? "";

        if (_template is TranscodingTemplate tt)
        {
            // Sync the Encoder string
            if (_factoryWidgets.TryGetValue("entEncoder", out var obj) && obj is Entry ent)
            {
                tt.EncoderSettings.Encoder = ent.GetText()?.Trim() ?? "";
            }

            // Sync the Type from DropDown
            if (_ddType != null)
            {
                var selectedItem = _ddType.GetSelectedItem() as StringObject;
                tt.Type = selectedItem?.String?.ToLower() ?? "video";
            }
        }
        else if (_template is ContainerTemplate ct)
        {
            // Sync the Muxer/Format string
            if (_factoryWidgets.TryGetValue("entCSContainerFormat", out var obj) && obj is Entry ent)
            {
                ct.Muxer = ent.GetText()?.Trim() ?? "";
            }
        }
        else if (_template is FilterTemplate ft)
        {
            // Sync the Type from DropDown
            if (_ddType != null)
            {
                var selectedItem = _ddType.GetSelectedItem() as StringObject;
                ft.Type = selectedItem?.String?.ToLower() ?? "video";
            }
        }

        // Finally, sync all parameters from the ListBoxes (Parameters, Filters, etc.)
        _syncParamsToTemplate();
    }

    private bool _checkParameterExists(ListBox lb, string key)
    {
        var child = lb.GetFirstChild();
        while (child != null)
        {
            if (child is ParameterRow row && row.Key == key)
            {
                return true;
            }
            child = child.GetNextSibling();
        }
        return false;
    }

    private bool _hasParameters()
    {
        return _template switch
        {
            TranscodingTemplate tt => tt.EncoderSettings?.Parameters?.Count > 0,
            ContainerTemplate ct => ct.Parameters.Count > 0,
            FilterTemplate ft => ft.Filters.Count > 0,
            _ => false
        };
    }

    private void _showWarning(string message)
    {
        var dialog = new MessageDialog()
        {
            TransientFor = this,
            Modal = true,
            DestroyWithParent = true,
            MessageType = MessageType.Warning,
            Text = message
        };
        dialog.AddButton("OK", 0);
        dialog.OnResponse += (s, e) => dialog.Destroy();
        dialog.Present();
    }

    private void _clearListBox(ListBox lb)
    {
        while (lb.GetFirstChild() is Widget child) lb.Remove(child);
    }

    private void _refreshFilterList()
    {
        if (_template is FilterTemplate ft)
            _populateFilterUiCommon(ft.ComplexFilters, ft.Filters);
        else if (_template is TranscodingTemplate tt)
            _populateFilterUiCommon(tt.EncoderSettings.UsesComplexFilters, tt.EncoderSettings.Filters);
    }

    private void _openFilterEditor(EncoderSettings.FilterSettings settings)
    {
        // Look up the schema in the cache to provide the editor with context (labels, ranges, etc.)
        if (_app.Cache.Filters.TryGetValue(settings.FilterName, out var schema))
        {
            var editor = new FilterParameterEditor(_app, this, settings, schema, _refreshFilterList);
            editor.Present();
        }
    }

    private void _connectTemplateButtons()
    {
        // Encoder Template Button
        if (_factoryWidgets.TryGetValue("btnESLoadTemplate", out var btnES) && _template is TranscodingTemplate tt)
        {
            ((Button)btnES).OnClicked += (s, e) =>
            {
                _syncUiToTemplate();
                TemplateApplier.LoadEncoderTemplate(this, _app, tt.EncoderSettings, tt.Type, _populateTemplateData);
            };  
        }

        // Filter Template Button
        if (_factoryWidgets.TryGetValue("btnFSLoadTemplate", out var btnFS))
        {
            // Works for both Transcoding and Filter templates
            EncoderSettings? target = _template switch
            {
                TranscodingTemplate t => t.EncoderSettings,
                FilterTemplate f => new EncoderSettings { Filters = f.Filters, UsesComplexFilters = f.ComplexFilters },
                _ => null
            };

            var streamType = _template switch
            {
                TranscodingTemplate t => t.Type,
                FilterTemplate f => f.Type,
                _ => ""
            };

            if (target != null)
            {
                ((Button)btnFS).OnClicked += (s, e) =>
                {
                    _syncUiToTemplate();
                    TemplateApplier.LoadFilterTemplate(this, _app, target, streamType, () =>
                        {
                            // Special case: if target was a temp object for FilterTemplate, sync back
                            if (_template is FilterTemplate ft)
                            {
                                ft.Filters = target.Filters;
                                ft.ComplexFilters = target.UsesComplexFilters;
                            }
                            _populateTemplateData();
                        });
                };
            }
        }

        // Container Template Button
        if (_factoryWidgets.TryGetValue("btnCSLoadContainerTemplate", out var btnCS) && _template is ContainerTemplate ct)
        {
            ((Button)btnCS).OnClicked += (s, e) =>
            {
                // We need a Job object for the shared helper, so we create a temporary one for the template
                var tempJob = new Job { Multiplexer = ct.Muxer, MuxerParameters = ct.Parameters };
                TemplateApplier.LoadContainerTemplate(this, _app, tempJob, ct.Muxer, () =>
                {
                    ct.Muxer = tempJob.Multiplexer;
                    ct.Parameters = tempJob.MuxerParameters;
                    _populateTemplateData();
                });
            };
        }
    }
}