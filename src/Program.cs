using FFGui.Core;

namespace FFGui;

public static class Program
{
    [STAThread]
    public static int Main(string[] args)
    {
        // Initialize the native library mapping first!
        Gtk.Module.Initialize();
        Gio.Module.Initialize();

        // Only log GTK errors when not in DEBUG
#if !DEBUG
        GLib.LogWriterFunc writerFunc = (logLevel, fields) =>
        {
            // Allow Errors (1) and Criticals (2) to pass through.
            // Suppress Warnings (3), Messages (4), and Info (5).
            if (logLevel <= GLib.LogLevelFlags.LevelCritical)
            {
                // Pass the allowed logs to the default system writer
                return GLib.Functions.LogWriterDefault(logLevel, fields, IntPtr.Zero);
            }

            // Mark as handled to suppress the output
            return GLib.LogWriterOutput.Handled;
        };

        GLib.Functions.LogSetWriterFunc(writerFunc);
#endif

        // ONLY NOW instantiate your class
        var app = new FFGui.Core.FFGuiApp();
        return app.Run(args.Length > 0 ? args : null);
    }
}