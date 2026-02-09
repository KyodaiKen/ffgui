namespace FFGui.Core;

public static class HelperFunctions
{
    public static string? FindInPath(string binaryName)
    {
        var fileName = OperatingSystem.IsWindows() ? $"{binaryName}.exe" : binaryName;
        var pathEnv = Environment.GetEnvironmentVariable("PATH");
        if (string.IsNullOrEmpty(pathEnv)) return null;

        var paths = pathEnv.Split(Path.PathSeparator);
        foreach (var path in paths)
        {
            var fullPath = Path.Combine(path, fileName);
            if (File.Exists(fullPath)) return fullPath;
        }
        return null;
    }

    public static string? ResolveBinary(string binaryName, string? customPath = null)
    {
        // Check custom path from settings if provided
        if (!string.IsNullOrEmpty(customPath))
        {
            var fullPath = Path.Combine(customPath, OperatingSystem.IsWindows() ? $"{binaryName}.exe" : binaryName);
            if (File.Exists(fullPath)) return fullPath;
        }

        // Check system PATH
        var pathFromEnv = HelperFunctions.FindInPath(binaryName);
        if (pathFromEnv != null) return pathFromEnv;

        // Check bundled 'codecs' folder
        var bundledPath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "codecs", "ffmpeg",
                            OperatingSystem.IsWindows() ? $"{binaryName}.exe" : binaryName);
        if (File.Exists(bundledPath)) return bundledPath;

        return null;
    }
}