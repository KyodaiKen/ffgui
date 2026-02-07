using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.RegularExpressions;
using System.Threading.Tasks;
using FFGui.Models;

namespace FFGui.Services;

public class FFmpegFilterParser : FFmpegBaseParser
{
    // Regex matches: Flags (T/S/C), Name, I/O (e.g., V->A), and Description
    private static readonly Regex FilterListRegex = new(@"^\s([T.][S.][C.]{0,1})\s+([\w-]+)\s+([AVN|]*->[AVN|]*)\s+(.*)$", RegexOptions.Compiled);

    public FFmpegFilterParser(string ffmpegPath = "ffmpeg") : base(ffmpegPath) { }

    public async Task<Dictionary<string, FFmpegFilter>> ParseAllAsync(ProgressCallback? onProgress = null)
    {
        var filters = new Dictionary<string, FFmpegFilter>();
        var output = await RunCmdAsync("-filters");
        
        var lines = output.Split(new[] { '\r', '\n' }, StringSplitOptions.RemoveEmptyEntries);

        for (int i = 0; i < lines.Length; i++)
        {
            var match = FilterListRegex.Match(lines[i]);
            if (!match.Success) continue;

            string flagsRaw = match.Groups[1].Value;
            string name = match.Groups[2].Value;
            string ioStr = match.Groups[3].Value;
            string descr = match.Groups[4].Value;

            onProgress?.Invoke(name, (double)i / lines.Length);

            // Parse I/O types (V -> video, A -> audio, N -> dynamic)
            var ioParts = ioStr.Split("->");
            string[] inputs = MapIoTypes(ioParts[0]);
            string[] outputs = MapIoTypes(ioParts[1]);

            // Determine if complex (multiple inputs/outputs or dynamic 'N')
            bool isDynamic = ioStr.Contains('N');
            bool isComplex = inputs.Length > 1 || outputs.Length > 1 || isDynamic;

            var filter = new FFmpegFilter
            {
                Description = descr.Trim(),
                IsDynamic = isDynamic,
                IsComplex = isComplex,
                Inputs = inputs,
                Outputs = outputs,
                Flags = new FFmpegFilterFlags
                {
                    Timeline = flagsRaw.Contains('T'),
                    SliceThreading = flagsRaw.Contains('S'),
                    CommandSupport = flagsRaw.Contains('C')
                },
                Parameters = new Dictionary<string, FFmpegParameter>()
            };

            // Deep probe for AVOptions
            string details = await RunCmdAsync($"-h filter={name}");
            if (!string.IsNullOrWhiteSpace(details) && !details.Contains("Unknown"))
            {
                var parameters = ParseAVOptions(details);

                // --- Ported Python Special Case: Scale Filter ---
                // In Python, 'sws_flags' choices are moved into the main 'flags' parameter for 'scale'
                if (name == "scale" && parameters.ContainsKey("flags") && parameters.ContainsKey("sws_flags"))
                {
                    var mainFlags = parameters["flags"];
                    var swsFlags = parameters["sws_flags"];
                    
                    mainFlags.Options = swsFlags.Options;
                    mainFlags.Type = "flags";
                    
                    parameters["flags"] = mainFlags;
                    parameters.Remove("sws_flags");
                }

                filter.Parameters = parameters;
            }

            filters[name] = filter;
        }

        return filters;
    }

    private string[] MapIoTypes(string raw)
    {
        var types = new List<string>();
        foreach (char c in raw)
        {
            switch (c)
            {
                case 'V': types.Add("video"); break;
                case 'A': types.Add("audio"); break;
                case 'N': types.Add("dynamic"); break;
            }
        }
        return types.ToArray();
    }
}