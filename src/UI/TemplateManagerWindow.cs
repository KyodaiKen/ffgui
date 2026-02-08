using Gtk;
using FFGui.Models;
using FFGui.Core;
using YamlDotNet.Serialization;
using YamlDotNet.Serialization.NamingConventions;
using Gio;
using File = System.IO.File;
using HarfBuzz;

namespace FFGui.UI;

public class TemplateManagerWindow : Window
{
    private class TemplateRow : ListBoxRow
    {
        public Template Template { get; init; } = null!;
    }

    private readonly FFGuiApp _app;
    private readonly Window _parent;
    private readonly bool _pickerMode;
    private readonly string _targetType;
    private readonly string _subType;
    private readonly Action<Template>? _onSelect;
    private readonly SizeGroup _sgType = new();
    private readonly SizeGroup _sgTarget = new();

    private ListBox _lstTemplates = null!;
    private SearchEntry _searchEntry = null!;
    private Button _btnApply = null!;
    private List<Template> _allTemplates = new();

    private readonly IDeserializer _yamlDeserializer;

    public TemplateManagerWindow(FFGuiApp app, Window parent) : this(app, parent, false, "", "", null) { }

    public TemplateManagerWindow(FFGuiApp app, Window parent, bool pickerMode, string targetType, string subType, Action<Template>? onSelect)
    {
        _app = app;
        _parent = parent;
        _pickerMode = pickerMode;
        _targetType = targetType;
        _subType = subType;
        _onSelect = onSelect;

        // Initialize YAML deserializer
        _yamlDeserializer = new DeserializerBuilder()
            .WithNamingConvention(PascalCaseNamingConvention.Instance)
            .IgnoreUnmatchedProperties()
            .Build();

        SetTitle(_pickerMode ? $"Select {_targetType} Template" : "Manage Templates");
        SetDefaultSize(800, 550);
        if (parent is not null) SetTransientFor(_parent);
        SetModal(true);

        BuildUI();
        LoadTemplates();
    }

    private void BuildUI()
    {
        var header = new HeaderBar();
        _searchEntry = new SearchEntry { PlaceholderText = "Filter templates..." };
        // Fix: Ensure we don't pass null to PopulateList
        _searchEntry.OnSearchChanged += (s, e) => PopulateList(_searchEntry.GetText() ?? "");
        header.SetTitleWidget(_searchEntry);
        SetTitlebar(header);

        var mainBox = new Box { Spacing = 8 };
        mainBox.SetOrientation(Orientation.Vertical);
        mainBox.SetMarginStart(12); mainBox.SetMarginEnd(12);
        mainBox.SetMarginTop(10); mainBox.SetMarginBottom(10);

        var listHeader = new Box { Spacing = 10, MarginStart = 8, MarginEnd = 12 };

        var lblType = new Label { Label_ = "<b>TYPE</b>", UseMarkup = true, Xalign = 0 };
        var lblTarget = new Label { Label_ = "<b>TARGET</b>", UseMarkup = true, Xalign = 0 };
        var lblName = new Label { Label_ = "<b>NAME</b>", UseMarkup = true, Xalign = 0, Hexpand = true };

        // Add to SizeGroups
        _sgType.Mode = SizeGroupMode.Horizontal;
        _sgType.AddWidget(lblType);
        _sgTarget.Mode = SizeGroupMode.Horizontal;
        _sgTarget.AddWidget(lblTarget);

        listHeader.Append(lblType);
        listHeader.Append(lblTarget);
        listHeader.Append(lblName);

        if (!_pickerMode)
        {
            // Align the Action header to the right
            listHeader.Append(new Label { Label_ = "<b>ACTIONS</b>", UseMarkup = true, Xalign = 1, WidthRequest = 120 });
        }
        mainBox.Append(listHeader);

        var scroll = new ScrolledWindow { Vexpand = true, HasFrame = true };
        _lstTemplates = new ListBox { SelectionMode = SelectionMode.Single };
        _lstTemplates.AddCssClass("boxed-list");
        _lstTemplates.OnSelectedRowsChanged += (s, e) => UpdateButtonSensitivity();
        _lstTemplates.OnRowActivated += (s, e) => { if (_pickerMode) _onApplyClicked(); };

        scroll.SetChild(_lstTemplates);
        mainBox.Append(scroll);

        var footer = new Box { Spacing = 6, Halign = Align.End };
        var btnCancel = new Button { Label = "Close" };
        btnCancel.OnClicked += (s, e) => Close();
        footer.Append(btnCancel);

        if (_pickerMode)
        {
            _btnApply = new Button { Label = "Apply Template" };
            _btnApply.AddCssClass("suggested-action");
            _btnApply.SetSensitive(false);
            btnCancel.Label = "Cancel";
            footer.Append(_btnApply);
            _btnApply.OnClicked += (s, e) => _onApplyClicked();
        }
        else
        {
            var btnNew = new MenuButton
            {
                IconName = "list-add-symbolic",
                TooltipText = "Create New Template"
            };

            // Load the menu from the string we just added to Menus.cs
            var builder = Builder.NewFromString(Menus.TemplateNewMenu, Menus.TemplateNewMenu.Length);
            
            var menuModel = builder.GetObject("template-new-menu") as MenuModel ?? throw new Exception("Menu model not found");
            btnNew.MenuModel = menuModel;

            var actionGroup = new SimpleActionGroup();
            // Fix: Follow JobRow's pattern for AddAction
            AddAction(actionGroup, "new_transcoding", (a, p) => _createNewTemplate(new TranscodingTemplate()));
            AddAction(actionGroup, "new_container", (a, p) => _createNewTemplate(new ContainerTemplate()));
            AddAction(actionGroup, "new_filter", (a, p) => _createNewTemplate(new FilterTemplate()));

            // Register the group under the prefix "tpl" (matching our XML)
            InsertActionGroup("tpl", actionGroup);

            footer.Append(btnNew);
        }

        mainBox.Append(footer);
        SetChild(mainBox);
    }

    private void LoadTemplates()
    {
        _allTemplates.Clear();

        foreach (var path in _app.TemplatePaths)
        {
            if (!Directory.Exists(path)) continue;

            // Adapt: Search for .yaml and .yml files
            string[] files = Directory.GetFiles(path, "*.y*ml");
            foreach (var file in files)
            {
                try
                {
                    string yaml = System.IO.File.ReadAllText(file);
                    Template? t = null;

                    // Polymorphic YAML detection based on content keys
                    if (yaml.Contains("EncoderSettings:"))
                        t = _yamlDeserializer.Deserialize<TranscodingTemplate>(yaml);
                    else if (yaml.Contains("Muxer:"))
                        t = _yamlDeserializer.Deserialize<ContainerTemplate>(yaml);
                    else if (yaml.Contains("Filters:"))
                        t = _yamlDeserializer.Deserialize<FilterTemplate>(yaml);

                    if (t != null)
                    {
                        // CAPTURE THE FILENAME HERE
                        t.Name = Path.GetFileNameWithoutExtension(file);
                        _allTemplates.Add(t);
                    }
                }
                catch { /* Log error or skip */ }
            }
        }
        PopulateList();
    }

    private void PopulateList(string filter = "")
    {
        while (_lstTemplates.GetFirstChild() is Widget child)
            _lstTemplates.Remove(child);

        var query = filter.ToLower();
        var filtered = _allTemplates.Where(t =>
            string.IsNullOrEmpty(query) ||
            t.Description.ToLower().Contains(query)
        );

        // Sort list
        filtered =
        [
            .. filtered
            .OrderBy(i => i switch
            {
                TranscodingTemplate _ => 0,
                FilterTemplate _      => 1,
                ContainerTemplate _   => 2,
                _ => 3
            })
            .ThenBy(i => i switch
            {
                TranscodingTemplate tt => tt.Type ?? "",
                ContainerTemplate ct   => ct.Muxer ?? "",
                FilterTemplate ft      => ft.Type ?? "",
                _ => ""
            }, StringComparer.OrdinalIgnoreCase)
            .ThenBy(i => i.Name ?? "", StringComparer.OrdinalIgnoreCase)
        ];


        foreach (var t in filtered)
        {
            if (_pickerMode)
            {
                if (t.GetType().ToString() != _targetType)
                    continue;

                if (t is TranscodingTemplate tt)
                    if (tt.Type != _subType)
                        continue;

                if (t is FilterTemplate ft)
                    if (ft.Type != _subType)
                        continue;
            }
            _lstTemplates.Append(CreateTemplateRow(t));
        }
    }

    private ListBoxRow CreateTemplateRow(Template t)
    {
        var row = new TemplateRow { Template = t }; // Tag the model here
        var box = new Box { Spacing = 10 };
        box.SetMarginStart(6); box.SetMarginEnd(6);
        box.SetMarginTop(4); box.SetMarginBottom(4);

        string typeStr = t switch
        {
            TranscodingTemplate => "TRANSCODING",
            ContainerTemplate => "CONTAINER",
            FilterTemplate => "FILTER",
            _ => "UNKNOWN"
        };

        string targetStr = t switch
        {
            TranscodingTemplate tt => tt.Type.ToUpper(),
            FilterTemplate ft => ft.Type.ToUpper(),
            ContainerTemplate ct => ct.Muxer.ToUpper(),
            _ => "N/A"
        };

        var lblType = new Label { Label_ = typeStr, Xalign = 0 };
        var lblTarget = new Label { Label_ = targetStr, Xalign = 0, Opacity = 0.7 };

        // Add to SizeGroups to sync width with Header
        _sgType.AddWidget(lblType);
        _sgTarget.AddWidget(lblTarget);

        box.Append(lblType);
        box.Append(lblTarget);

        box.Append(new Label { Label_ = t.Name, Xalign = 0, Hexpand = true, Ellipsize = Pango.EllipsizeMode.End });

        // --- Path Logic to detect Read-Only ---
        // In your app, index 0 is typically the system path, index 1 is user path
        bool isReadOnly = false;
        if (_app.TemplatePaths.Length > 1)
        {
            var systemPath = _app.TemplatePaths[0];
            // Check if the template file exists in the system directory
            var expectedSystemFile = Path.Combine(systemPath, $"{t.Name}.yaml");
            if (File.Exists(expectedSystemFile) && !_app.PortableMode) isReadOnly = true;
        }

        if (!_pickerMode)
        {
            var actionBox = new Box { Spacing = 4 };

            // 1. Move Clone Button into the row (Available for everyone)
            var btnCloneRow = Button.NewFromIconName("edit-copy-symbolic");
            btnCloneRow.TooltipText = "Clone Template";
            btnCloneRow.AddCssClass("flat");
            btnCloneRow.OnClicked += (s, e) => _onCloneClicked(t); // Modified to accept template
            actionBox.Append(btnCloneRow);

            // 2. Add Edit/Rename/Delete ONLY if not Read-Only
            if (!isReadOnly)
            {
                var btnEdit = Button.NewFromIconName("document-edit-symbolic");
                btnEdit.TooltipText = "Edit Template";
                btnEdit.AddCssClass("flat");
                btnEdit.OnClicked += (s, e) => _onEditClicked(t);
                actionBox.Append(btnEdit);

                var btnRename = Button.NewFromIconName("insert-text-symbolic");
                btnRename.TooltipText = "Rename Template";
                btnRename.AddCssClass("flat");
                btnRename.OnClicked += (s, e) => _onRenameClicked(t);
                actionBox.Append(btnRename);

                var btnDelete = Button.NewFromIconName("user-trash-symbolic");
                btnDelete.TooltipText = "Delete Template";
                btnDelete.AddCssClass("flat");
                btnDelete.AddCssClass("destructive-action");
                btnDelete.OnClicked += (s, e) => _onDeleteClicked(t);
                actionBox.Append(btnDelete);
            }
            else
            {
                // Optional: Add a lock icon for visual feedback
                var lblLocked = Image.NewFromIconName("changes-prevent-symbolic");
                lblLocked.TooltipText = "System Template (Read-Only)";
                lblLocked.Opacity = 0.5;
                actionBox.Append(lblLocked);
            }

            box.Append(actionBox);
        }

        row.SetChild(box);
        return row;
    }

    private void UpdateButtonSensitivity()
    {
        bool hasSelection = _lstTemplates.GetSelectedRow() != null;
        if (_pickerMode) _btnApply.SetSensitive(hasSelection);
    }

    private void AddAction(SimpleActionGroup group, string name, Action<SimpleAction, GLib.Variant?> callback)
    {
        var action = SimpleAction.New(name, null);
        action.OnActivate += (s, e) => callback(s, e.Parameter);
        group.AddAction(action);
    }

    private void _createNewTemplate(Template tpl)
    {
        // Launch editor in 'New' mode
        var editor = new TemplateEditorWindow(_app, tpl, EditorMode.New, (savedTpl, name) =>
        {
            _saveTemplateToDisk(savedTpl, name);
            LoadTemplates(); // Refresh the list
        });
        editor.SetTransientFor(this);
        editor.Present();
    }

    private void _saveTemplateToDisk(Template tpl, string name)
    {

        if (_app.TemplatePaths == null)
        {
            Console.WriteLine("Error: User template path (index 1) is not configured.");
            return;
        }
        var userPath = "";
        if (_app.TemplatePaths.Length == 1)
        {
            // Portable mode
            userPath = _app.TemplatePaths[0];
        }
        else
        {
            // Installed mode
            userPath = _app.TemplatePaths[1];
        }

        if (!Directory.Exists(userPath)) Directory.CreateDirectory(userPath);

        // Use the TemplateName set by the editor
        var filePath = Path.Combine(userPath, $"{name}.yaml");

        var serializer = new SerializerBuilder()
            .WithNamingConvention(PascalCaseNamingConvention.Instance)
            .Build();

        var yaml = serializer.Serialize(tpl);
        System.IO.File.WriteAllText(filePath, yaml);
    }

    private void _onDeleteClicked(Template? t = null)
    {
        var selectedTemplate = t ?? _getSelectedTemplate();
        if (selectedTemplate == null) return;

        // FIX: Handle both Installed (Length=2) and Portable (Length=1) modes
        string userPath;
        if (_app.TemplatePaths.Length > 1)
        {
            // Installed Mode: User templates are at index 1
            userPath = _app.TemplatePaths[1];
        }
        else if (_app.TemplatePaths.Length == 1)
        {
            // Portable Mode: Templates are at index 0
            userPath = _app.TemplatePaths[0];
        }
        else
        {
            return; // Should not happen
        }

        // Use the Name property we added to the model
        var filePath = Path.Combine(userPath, $"{selectedTemplate.Name}.yaml");

        if (System.IO.File.Exists(filePath))
        {
            System.IO.File.Delete(filePath);
            LoadTemplates();
        }
        else
        {
            Console.WriteLine($"Cannot delete '{selectedTemplate.Name}'. It might be a system template or read-only.");
        }
    }

    private void _onRenameClicked(Template t)
    {
        // Simple input dialog using a Window
        var dialog = new Window { Title = "Rename Template", Modal = true, TransientFor = this };
        dialog.SetDefaultSize(300, 100);

        var box = new Box { Spacing = 10, MarginTop = 12, MarginBottom = 12, MarginStart = 12, MarginEnd = 12 };
        box.SetOrientation(Orientation.Vertical);

        var entry = new Entry { Text_ = t.Name };
        Entry.ActivateSignal.Connect(entry, (sender, e) =>
        {
            _performRename(t, entry.GetText());
            dialog.Close();
        });

        var btnBox = new Box { Spacing = 6, Halign = Align.End };
        var btnCancel = new Button { Label = "Cancel" };
        btnCancel.OnClicked += (s, e) => dialog.Close();

        var btnSave = new Button { Label = "Rename" };
        btnSave.AddCssClass("suggested-action");
        btnSave.OnClicked += (s, e) =>
        {
            _performRename(t, entry.GetText());
            dialog.Close();
        };

        btnBox.Append(btnCancel);
        btnBox.Append(btnSave);

        box.Append(new Label { Label_ = "Enter new name:", Xalign = 0 });
        box.Append(entry);
        box.Append(btnBox);

        dialog.SetChild(box);
        dialog.Present();
    }

    private void _onEditClicked(Template? t = null)
    {
        // If called from the ListBox activation (null), get selected
        var selectedTemplate = t ?? _getSelectedTemplate();
        if (selectedTemplate == null) return;

        var editor = new TemplateEditorWindow(_app, selectedTemplate, EditorMode.Edit, (savedTpl, name) =>
        {
            _saveTemplateToDisk(savedTpl, name);
            LoadTemplates();
        });
        editor.SetTransientFor(this);
        editor.Present();
    }

    private void _onCloneClicked(Template? t = null)
    {
        var selectedTemplate = t ?? _getSelectedTemplate();
        if (selectedTemplate == null) return;

        var serializer = new SerializerBuilder().WithNamingConvention(PascalCaseNamingConvention.Instance).Build();
        var yaml = serializer.Serialize(selectedTemplate);

        Template? clonedTemplate = null;
        if (selectedTemplate is TranscodingTemplate) clonedTemplate = _yamlDeserializer.Deserialize<TranscodingTemplate>(yaml);
        else if (selectedTemplate is ContainerTemplate) clonedTemplate = _yamlDeserializer.Deserialize<ContainerTemplate>(yaml);
        else if (selectedTemplate is FilterTemplate) clonedTemplate = _yamlDeserializer.Deserialize<FilterTemplate>(yaml);

        if (clonedTemplate != null)
        {
            clonedTemplate.Description += " (Clone)";
            _createNewTemplate(clonedTemplate);
        }
    }

    private void _onDeleteClicked()
    {
        var selectedTemplate = _getSelectedTemplate();
        if (selectedTemplate == null) return;

        // Warning: System templates (Path index 0) should probably be read-only
        // We only delete from the User path (Path index 1)
        string safeName = string.Concat(selectedTemplate.Description.Split(Path.GetInvalidFileNameChars())).Replace(" ", "_");
        var userFilePath = Path.Combine(_app.TemplatePaths[1], $"{safeName}.yaml");

        if (System.IO.File.Exists(userFilePath))
        {
            System.IO.File.Delete(userFilePath);
            LoadTemplates();
        }
        else
        {
            // Optional: show a message that system templates cannot be deleted
            Console.WriteLine("Cannot delete system template.");
        }
    }

    private void _onApplyClicked()
    {
        var selectedTemplate = _getSelectedTemplate();
        if (selectedTemplate != null && _onSelect != null)
        {
            _onSelect(selectedTemplate);
            Close();
        }
    }

    private void _performRename(Template t, string newName)
    {
        newName = newName.Trim();
        if (string.IsNullOrEmpty(newName) || newName == t.Name) return;

        // Determine user path safely
        var userPath = _app.TemplatePaths.Length > 1 ? _app.TemplatePaths[1] : _app.TemplatePaths[0];

        var oldPath = Path.Combine(userPath, $"{t.Name}.yaml");
        var newPath = Path.Combine(userPath, $"{newName}.yaml");

        if (File.Exists(newPath))
        {
            Console.WriteLine("Error: A template with that name already exists.");
            return;
        }

        if (File.Exists(oldPath))
        {
            try
            {
                File.Move(oldPath, newPath);
                t.Name = newName; // Update model
                LoadTemplates(); // Refresh UI
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Rename failed: {ex.Message}");
            }
        }
        else
        {
            Console.WriteLine("Error: Cannot find original template file. It might be a system template.");
        }
    }

    // Helper to get the template model from the selected ListBoxRow
    private Template? _getSelectedTemplate()
    {
        if (_lstTemplates.GetSelectedRow() is TemplateRow tRow)
        {
            return tRow.Template;
        }
        return null;
    }
}