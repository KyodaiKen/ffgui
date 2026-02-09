namespace FFGui.UI;

using Gtk;

public partial class JobEditorWindow
{
    private bool _onSourceListFilesDrop(Gtk.DropTarget sender, Gtk.DropTarget.DropSignalArgs args, ListBox lb)
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
                var handle = new GObject.Internal.ObjectHandle(filePtr, false);
                var file = new Gio.FileHelper(handle);

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
            _ = _addSourceFiles(paths, lb);
            return true;
        }

        return false;
    }
}
