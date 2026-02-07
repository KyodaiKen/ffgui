namespace FFGui.UI;

using Gtk;
using FFGui.Models;
using System.Collections.Generic;
using FFGui.Core;

public static class TemplateApplier
{
    private static async Task<int> AskMergeReplace(Window parent, string title, int count)
    {
        // Rule: ONLY import parameters when they are EMPTY, if not, use a dialog
        if (count == 0) return 1; // Index 1 is "Add" (safe default)

        var alert = new AlertDialog
        {
            Message = $"{title} has existing data",
            Detail = $"There are currently {count} items defined. Would you like to add the template data to the current list or replace it entirely?"
        };
        alert.SetButtons(new string[] { "Cancel", "Add", "Replace" });
        alert.SetCancelButton(0);
        alert.SetDefaultButton(1);

        try
        {
            return await alert.ChooseAsync(parent);
        }
        catch (Exception ex)
        {
            Console.WriteLine($"Dialog error: {ex.Message}");
            return 0; // Cancel
        }
    }

    public static void LoadEncoderTemplate(Window parent, FFGuiApp app, EncoderSettings target, string streamType, Action onRefresh)
    {
        var picker = new TemplateManagerWindow(app, parent, true, typeof(TranscodingTemplate).FullName!, streamType, async (template) =>
        {
            if (template is not TranscodingTemplate tt) return;
            if (tt.EncoderSettings is null) return;
            if (tt.EncoderSettings.Parameters is null) return;

            target ??= new();
            target.Parameters ??= [];

            int response = await AskMergeReplace(parent, "Encoder Parameters", target.Parameters.Count);
            if (response == 0) return; // Cancel

            if (response == 2) target.Parameters.Clear(); // Replace

            // Apply parameters (Merge or overwrite)
            foreach (var p in tt.EncoderSettings.Parameters)
                target.Parameters[p.Key] = p.Value;

            target.Encoder = tt.EncoderSettings.Encoder;
            onRefresh();
        });
        picker.Present();
    }

    public static void LoadFilterTemplate(Window parent, FFGuiApp app, EncoderSettings target, string streamType, Action onRefresh)
    {
        var picker = new TemplateManagerWindow(app, parent, true, typeof(FilterTemplate).FullName!, streamType, async (template) =>
        {
            if (template is not FilterTemplate ft) return;

            int response = await AskMergeReplace(parent, "Filters", target.Filters.Count);
            if (response == 0) return;

            if (response == 2) target.Filters.Clear();
            target.Filters.AddRange(ft.Filters);
            target.UsesComplexFilters = ft.ComplexFilters;
            onRefresh();
        });
        picker.Present();
    }

    public static void LoadContainerTemplate(Window parent, FFGuiApp app, Job job, string container, Action onRefresh)
    {
        var picker = new TemplateManagerWindow(app, parent, true, typeof(ContainerTemplate).FullName!, container, async (template) =>
        {
            if (template is not ContainerTemplate ct) return;

            int response = await AskMergeReplace(parent, "Muxer Parameters", job.MuxerParameters.Count);
            if (response == 0) return;

            if (response == 2) job.MuxerParameters.Clear();

            // Apply the Muxer string
            job.Multiplexer = ct.Muxer;

            // Apply parameters
            foreach (var p in ct.Parameters)
                job.MuxerParameters[p.Key] = p.Value;

            onRefresh();
        });
        picker.Present();
    }
}