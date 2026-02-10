namespace FFGui.UI;

using Gtk;
using FFGui.Models;

public class ParameterRow : ListBoxRow
{
    public string Key { get; set; } = "";
    public Widget ValueWidget { get; set; } = null!;
    public FFmpegParameter? Schema { get; set; }
}

public class FlagsValueWidget : Box
{
    public string CurrentValue { get; set; } = "";
    public FlowBox FlowBox { get; init; }
    public Button SearchButton { get; init; }

    public FlagsValueWidget()
    {
        Spacing = 6;
        SetOrientation(Orientation.Horizontal);

        FlowBox = new FlowBox
        {
            SelectionMode = SelectionMode.None,
            ColumnSpacing = 4,
            RowSpacing = 4,
            Hexpand = true,
            Valign = Align.Center
        };

        SearchButton = Button.NewFromIconName("search-symbolic");
        SearchButton.Valign = Align.Center;
        SearchButton.AddCssClass("flat");

        Append(FlowBox);
        Append(SearchButton);
    }
}

static class ParameterRowFactory
{
    public static ParameterRow CreateParameterRow(string key, object? value, FFmpegParameter? schema, Action<ParameterRow> onRemove, Action? onChanged)
    {
        var box = new Box { Spacing = 12, MarginStart = 6, MarginEnd = 6, MarginTop = 4, MarginBottom = 4 };

        // Label
        var lbl = new Label { Label_ = $"<b>{key}</b>", UseMarkup = true, Xalign = 0, WidthRequest = 120, Ellipsize = Pango.EllipsizeMode.End };
        if (!string.IsNullOrEmpty(schema?.Description)) lbl.TooltipText = schema.Description;
        box.Append(lbl);

        // Value Widget (using the factory below)

        var valueWidget = BuildValueWidget(key, value, schema, onChanged);
        valueWidget.Hexpand = true;
        box.Append(valueWidget);
        var row = new ParameterRow { Key = key, Schema = schema, ValueWidget = valueWidget };

        // Remove Button
        var btnRemove = Button.NewFromIconName("user-trash-symbolic");
        btnRemove.AddCssClass("flat");
        btnRemove.OnClicked += (s, e) => onRemove(row);
        box.Append(btnRemove);

        row.SetChild(box);
        return row;
    }

    public static Widget BuildValueWidget(string key, object? value, FFmpegParameter? schema, Action? onChanged)
    {
        if (schema == null)
        {
            var entry = new Entry { Text_ = value?.ToString() ?? "" };
            entry.OnChanged += (s, e) => onChanged?.Invoke();
            return entry;
        }

        string pType = schema.Type.ToLower();
        var options = schema.Options;

        // FLAGS
        if (pType == "flags" && options != null)
        {
            var flagsWidget = new FlagsValueWidget();

            if (value is FFmpegValueLong { Value: 0 }) flagsWidget.CurrentValue = "";
            else flagsWidget.CurrentValue = value?.ToString() ?? "";

            Action refreshFlow = null!;
            refreshFlow = () =>
            {
                while (flagsWidget.FlowBox.GetFirstChild() is Widget child) flagsWidget.FlowBox.Remove(child);

                var currentFlags = flagsWidget.CurrentValue.Split('+', StringSplitOptions.RemoveEmptyEntries);

                if (currentFlags.Length == 0)
                {
                    flagsWidget.FlowBox.Append(new Label
                    {
                        Label_ = "Select...",
                        Opacity = 0.5,
                        MarginStart = 6,
                        Halign = Align.Start
                    });
                }
                else
                {
                    foreach (var flag in currentFlags)
                    {
                        var pill = new Box { Spacing = 4 };
                        pill.AddCssClass("pill");
                        pill.Append(new Label { Label_ = flag });

                        var btnRemove = Button.NewFromIconName("user-trash-symbolic");
                        btnRemove.AddCssClass("flat");
                        btnRemove.SetSizeRequest(16, 16);

                        btnRemove.OnClicked += (s, e) =>
                        {
                            var remaining = flagsWidget.CurrentValue.Split('+')
                                .Where(f => f.Trim() != flag.Trim());
                            flagsWidget.CurrentValue = string.Join("+", remaining);
                            refreshFlow();
                            onChanged?.Invoke();
                        };

                        pill.Append(btnRemove);
                        flagsWidget.FlowBox.Append(pill);
                    }
                }
            };

            flagsWidget.SearchButton.OnClicked += (s, e) =>
            {
                // FlagsPickerWindow requires the key, the options dictionary, 
                // the current value string, and the callback.
                var picker = new FlagsPickerWindow(
                    key: key,
                    options: options,
                    current: flagsWidget.CurrentValue,
                    onApply: (newValue) =>
                    {
                        flagsWidget.CurrentValue = newValue;
                        refreshFlow();
                        onChanged?.Invoke();
                    }
                );

                // Since FlagsPickerWindow is a Gtk.Window, we present it
                picker.SetTransientFor(flagsWidget.GetRoot() as Window);
                picker.Present();
            };

            refreshFlow();
            return flagsWidget;
        }

        // DROPDOWN
        if (options != null && options.Count > 0 && pType != "flags")
        {
            var displayNames = options.Select(o => string.IsNullOrEmpty(o.Value.Description) ? o.Key : $"{o.Key} ({o.Value.Description})").ToArray();
            var dd = DropDown.NewFromStrings(displayNames);

            string curVal = value?.ToString() ?? "";
            int idx = options.Keys.ToList().IndexOf(curVal);
            if (idx >= 0) dd.SetSelected((uint)idx);

            dd.OnNotify += (s, e) =>
            {
                if (e.Pspec.GetName() == "selected") onChanged?.Invoke();
            };
            return dd;
        }

        // NUMERIC
        if (pType.Contains("int") || pType.Contains("float") || pType.Contains("double"))
        {
            bool isFloat = pType.Contains("float") || pType.Contains("double");

            double vMin = _parseFFmpegNum(schema.Min, -2147483648);
            double vMax = _parseFFmpegNum(schema.Max, 2147483647);
            double vCur = _parseFFmpegNum(value ?? schema.Default, 0);

            double step = isFloat ? 0.01 : 1.0;
            var adj = Adjustment.New(vCur, vMin, vMax, step, step * 10, 0);

            var spin = SpinButton.New(adj, step, (uint)(isFloat ? 6 : 0)); // 6 digits for floats
            spin.Numeric = true;
            return spin;
        }

        // RATIONAL
        if (pType.Contains("rational"))
        {
            var entry = new Entry
            {
                Text_ = value?.ToString() ?? "",
                PlaceholderText = "4:3, 60000/1001"
            };
            entry.OnChanged += (s, e) => onChanged?.Invoke();
            return entry;
        }

        // BOOLEAN
        if (pType == "bool" || pType == "boolean")
        {
            bool active = value?.ToString()?.ToLower() == "true" || value?.ToString() == "1";
            var sw = new Switch { Active = active, Halign = Align.Start };

            sw.OnNotify += (s, e) =>
            {
                if (e.Pspec.GetName() == "active") onChanged?.Invoke();
            };
            return sw;
        }

        // DEFAULT (Text)
        var defEntry = new Entry { Text_ = value?.ToString() ?? "" };
        defEntry.OnChanged += (s, e) => onChanged?.Invoke(); // Hook change
        return defEntry;
    }

    public static object? ExtractWidgetValue(Widget widget, FFmpegParameter? schema)
    {
        if (widget is DropDown dd)
        {
            if (schema?.Options == null) return null;
            return schema.Options.Keys.ElementAtOrDefault((int)dd.Selected);
        }

        if (widget is FlagsValueWidget fvw)
        {
            return fvw.CurrentValue;
        }

        if (widget is SpinButton spin) return spin.Digits > 0 ? spin.Value : (long)spin.Value;
        if (widget is Switch sw) return sw.Active;
        if (widget is Entry entry) return entry.Text_;

        return null;
    }

    private static double _parseFFmpegNum(object? val, double fallback)
    {
        if (val is IFFmpegValue fVal)
        {
            return fVal switch
            {
                FFmpegValueLong v => v.Value,
                FFmpegValueDouble v => v.Value,
                FFmpegValueString v => double.TryParse(v.Value, out var d) ? d : fallback,
                _ => fallback
            };
        }
        if (val == null) return fallback;
        return double.TryParse(val.ToString(), out var res) ? res : fallback;
    }
}