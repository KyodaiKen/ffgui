namespace FFGui.Helpers;

using System;
using System.Globalization;
using System.Text.RegularExpressions;


public static class LanguageHelper
{
    private static Dictionary<string, string> _languages = new();

    public static void Initialize()
    {
        string path = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "lng.psv");

        if (!File.Exists(path))
        {
            Console.WriteLine($"[Error] Language file not found: {path}");
            return;
        }

        try
        {
            // Encoding.UTF8 automatically detects and strips the BOM
            // File.ReadAllLines handles both \n and \r\n (0D0A) line endings
            string[] lines = File.ReadAllLines(path, System.Text.Encoding.UTF8);

            _languages.Clear();
            foreach (var line in lines)
            {
                if (string.IsNullOrWhiteSpace(line)) continue;

                // Split by pipe
                var parts = line.Split('|');

                if (parts.Length >= 2)
                {
                    // parts[0] is the code, parts[3] is the name
                    string code = parts[0].Trim();
                    string name = parts[3].Trim();

                    _languages[code] = name;
                }
            }
        }
        catch (Exception ex)
        {
            Console.WriteLine($"[Error] Failed to load languages: {ex.Message}");
        }
    }

    public static Dictionary<string, string> GetAll() => _languages;
}

public static class FFmpegTimeParser
{
    /// <summary>
    /// Converts an FFmpeg duration string to a TimeSpan.
    /// Supports: [-]HH:MM:SS[.m...], [-]S+[.m...][unit] (s, ms, us)
    /// </summary>
    public static bool TryParse(string input, out TimeSpan result)
    {
        result = TimeSpan.Zero;
        if (string.IsNullOrWhiteSpace(input)) return false;

        input = input.Trim().ToLowerInvariant();

        // Handle Sexagesimal format: [HOURS:]MINUTES:SECONDS[.m...]
        // Example: 12:03:45 or 03:45
        if (input.Contains(':'))
        {
            var parts = input.Split(':');
            try
            {
                if (parts.Length == 3) // HH:MM:SS
                {
                    if (double.TryParse(parts[2], CultureInfo.InvariantCulture, out double seconds))
                    {
                        int h = int.Parse(parts[0]);
                        int m = int.Parse(parts[1]);
                        result = TimeSpan.FromHours(h) + TimeSpan.FromMinutes(m) + TimeSpan.FromSeconds(seconds);
                        return true;
                    }
                }
                else if (parts.Length == 2) // MM:SS
                {
                    if (double.TryParse(parts[1], CultureInfo.InvariantCulture, out double seconds))
                    {
                        int m = int.Parse(parts[0]);
                        result = TimeSpan.FromMinutes(m) + TimeSpan.FromSeconds(seconds);
                        return true;
                    }
                }
            }
            catch { return false; }
        }

        // Handle Seconds format with optional units: S+[.m...][unit]
        // Units: 's' (default), 'ms', 'us' / 'μs'
        var match = Regex.Match(input, @"^(?<value>-?[\d.]+)(?<unit>ms|us|μs|s)?$");
        if (match.Success)
        {
            if (double.TryParse(match.Groups["value"].Value, CultureInfo.InvariantCulture, out double val))
            {
                string unit = match.Groups["unit"].Value;

                result = unit switch
                {
                    "ms" => TimeSpan.FromMilliseconds(val),
                    "us" => TimeSpan.FromTicks((long)(val * 10)), // 1 tick = 100ns, so 1us = 10 ticks
                    "μs" => TimeSpan.FromTicks((long)(val * 10)),
                    _ => TimeSpan.FromSeconds(val) // default or 's'
                };
                return true;
            }
        }

        return false;
    }
}