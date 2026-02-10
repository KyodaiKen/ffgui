using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.RegularExpressions;
using System.Threading.Tasks;
using FFGui.Models;

namespace FFGui.Services;

public class FFmpegGlobalsParser : FFmpegBaseParser
{
    // Regex for standard (non-AVOption) global flags like "-v quiet"
    private static readonly Regex StdParamRegex = new(@"^\s*-([\w:\[\]<>+-]+)(?:\s+(<[^>]*>))?\s+(.*)$", RegexOptions.Compiled);

    // Map Python-style headers to our Model sections
    private readonly Dictionary<string, string> _headerToSection = new()
    {
        { "Advanced per-stream options", "per_stream" },
        { "Video options", "video" },
        { "Advanced Video options", "video" },
        { "Audio options", "audio" },
        { "Advanced Audio options", "audio" },
        { "Subtitle options", "subtitle" },
        { "Advanced Subtitle options", "subtitle" },
        { "AVCodecContext AVOptions", "av_options" }
    };

    public FFmpegGlobalsParser(string ffmpegPath = "ffmpeg") : base(ffmpegPath) { }

    public async Task<FFmpegGlobalParameters> ParseGlobalsAsync(ProgressCallback? onProgress = null)
    {
        var globals = new FFmpegGlobalParameters
        {
            Video = new(),
            Audio = new(),
            Subtitle = new(),
            PerStream = new()
        };

        string output = await RunCmdAsync("-h full");
        var lines = output.Split(new[] { '\r', '\n' }, StringSplitOptions.RemoveEmptyEntries);

        string? currentSection = null;
        FFmpegParameter? lastParam = null;

        for (int i = 0; i < lines.Length; i++)
        {
            string line = lines[i];
            
            // Header Detection (Python: endswith(":") or "AVOptions" in line)
            if (line.TrimEnd().EndsWith(":") || line.Contains("AVOptions"))
            {
                string header = line.Trim().TrimEnd(':');
                _headerToSection.TryGetValue(header, out currentSection);
                lastParam = null;
                continue;
            }

            if (string.IsNullOrEmpty(currentSection)) continue;

            onProgress?.Invoke("Global Options", (double)i / lines.Length);

            // Handle AVOptions (Complex parameters with nested choices)
            if (currentSection == "av_options")
            {
                var pMatch = ParamRegex.Match(line);
                if (pMatch.Success)
                {
                    string name = Regex.Replace(pMatch.Groups[1].Value, @"\[.*\]", ""); // Clean stream specifiers
                    var (clean, min, max, def) = CleanDescriptor(pMatch.Groups[4].Value);
                    
                    var param = new FFmpegParameter
                    {
                        Type = pMatch.Groups[2].Value,
                        Description = clean,
                        Context = MapContext(pMatch.Groups[3].Value),
                        Min = min,
                        Max = max,
                        Default = def,
                        Options = new Dictionary<string, FFmpegOption>()
                    };

                    // Route to specific dictionaries based on flags (Python: _determine_target_sections)
                    RouteParameter(globals, name, param);
                    lastParam = param;
                }
                else if (lastParam != null)
                {
                    // Nested choice parsing
                    var oMatch = OptionRegex.Match(line);
                    if (oMatch.Success)
                    {
                        string optName = oMatch.Groups[1].Value;
                        string optValStr = oMatch.Groups[2].Value;
                        lastParam.Options![optName] = new FFmpegOption
                        {
                            Value = ToValue(string.IsNullOrEmpty(optValStr) ? optName : optValStr),
                            Description = oMatch.Groups[4].Value.Trim(),
                            Context = MapContext(oMatch.Groups[3].Value)
                        };
                    }
                }
            }
            else
            {
                // Handle Standard Global Options (Python: std_pattern)
                var stdMatch = StdParamRegex.Match(line);
                if (stdMatch.Success)
                {
                    string name = Regex.Replace(stdMatch.Groups[1].Value, @"\[.*\]", "");
                    string type = stdMatch.Groups[2].Value.Trim('<', '>');
                    string descr = stdMatch.Groups[3].Value;

                    var param = new FFmpegParameter
                    {
                        Type = type,
                        Description = descr.Trim(),
                        Context = new FFmpegContext(), // Standard globals usually don't have bitflags
                        Options = new Dictionary<string, FFmpegOption>()
                    };

                    // Route based on the current header category
                    switch (currentSection)
                    {
                        case "video": SafeAdd(globals.Video, name, param); break;
                        case "audio": SafeAdd(globals.Audio, name, param); break;
                        case "subtitle": SafeAdd(globals.Subtitle, name, param); break;
                        case "per_stream": SafeAdd(globals.PerStream, name, param); break;
                    }
                }
            }
        }

        return globals;
    }

    //Helpers
    private void RouteParameter(FFmpegGlobalParameters globals, string name, FFmpegParameter param)
    {
        bool routed = false;
        if (param.Context.Video) { SafeAdd(globals.Video, name, param); routed = true; }
        if (param.Context.Audio) { SafeAdd(globals.Audio, name, param); routed = true; }
        if (param.Context.Subtitle) { SafeAdd(globals.Subtitle, name, param); routed = true; }

        // If no specific media flag, it's a general stream option
        if (!routed) SafeAdd(globals.PerStream, name, param);
    }

    private void SafeAdd(Dictionary<string, FFmpegParameter> dict, string name, FFmpegParameter param)
    {
        if (dict.ContainsKey(name))
        {
            // If the description and type are identical, it's a true redundant duplicate. Skip it.
            if (dict[name].Description == param.Description && dict[name].Type == param.Type)
                return;

            // Otherwise, add with a suffix so the user can see both in the UI.
            // We use a suffix like " (AV)" to indicate it's an AVOption version.
            string uniqueName = $"{name} (AV)";

            // Ensure even the suffix doesn't collide (unlikely, but safe)
            int counter = 1;
            while (dict.ContainsKey(uniqueName))
            {
                uniqueName = $"{name} (AV-{counter++})";
            }

            dict[uniqueName] = param;
        }
        else
        {
            dict[name] = param;
        }
    }
}