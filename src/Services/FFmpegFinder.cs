using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Runtime.InteropServices;
using System.IO;
using System.Threading.Tasks;

public static class FFmpegFinder
{
    // Made static so it's accessible without instantiation
    public static async Task<List<string>> LocateBinariesAsync()
    {
        // Wrapping in Task.Run because disk-wide searches are I/O intensive
        return await Task.Run(() =>
        {
            if (RuntimeInformation.IsOSPlatform(OSPlatform.Windows))
            {
                return SearchWindows();
            }
            
            if (RuntimeInformation.IsOSPlatform(OSPlatform.Linux) || 
                RuntimeInformation.IsOSPlatform(OSPlatform.OSX))
            {
                return SearchUnix();
            }

            return new List<string>();
        });
    }

    private static List<string> SearchWindows()
    {
        string psCommand = "Get-ChildItem -Path C:\\ -Include ffmpeg.exe -Recurse -ErrorAction SilentlyContinue | " +
                           "Where-Object { $_.FullName -notmatch 'Windows|Appx|Package' } | " +
                           "Select-Object -ExpandProperty FullName";

        return RunProcess("powershell.exe", $"-NoProfile -ExecutionPolicy Bypass -Command \"{psCommand}\"");
    }

    private static List<string> SearchUnix()
    {
        string findCommand = "find / -type f -name \"ffmpeg\" -executable " +
                             "-not -path \"*/flatpak/*\" -not -path \"*/.local/*\" 2>/dev/null";

        return RunProcess("/bin/sh", $"-c '{findCommand}'");
    }

    private static List<string> RunProcess(string fileName, string arguments)
    {
        var paths = new List<string>();

        try
        {
            var startInfo = new ProcessStartInfo
            {
                FileName = fileName,
                Arguments = arguments,
                RedirectStandardOutput = true,
                UseShellExecute = false,
                CreateNoWindow = true
            };

            using var process = Process.Start(startInfo);
            if (process == null) return paths;

            using var reader = process.StandardOutput;
            while (!reader.EndOfStream)
            {
                string? line = reader.ReadLine()?.Trim();
                // Basic validation: ignore empty lines and ensure the file is still there
                if (!string.IsNullOrEmpty(line) && File.Exists(line))
                {
                    paths.Add(line);
                }
            }
        }
        catch (Exception ex)
        {
            // Log to your FFGUI debug console
            Console.WriteLine($"FFGUI Finder Error: {ex.Message}");
        }

        return paths;
    }
}