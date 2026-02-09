using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.RegularExpressions;
using System.Threading.Tasks;
using FFGui.Models;

namespace FFGui.Services;

public class FFmpegFormatParser : FFmpegBaseParser
{
    private static readonly Regex FormatListRegex = new(@"^\s([D\s])([E\s])\s+([\w,]+)\s+(.*)$", RegexOptions.Compiled);
    
    // Regex to capture extensions, trimming the trailing dot if present
    private static readonly Regex ExtensionRegex = new(@"Common extensions:\s+([\w,.]+)", RegexOptions.Compiled);

    public FFmpegFormatParser(string ffmpegPath = "ffmpeg") : base(ffmpegPath) { }

    public async Task<Dictionary<string, FFmpegFormat>> ParseAllAsync(ProgressCallback? onProgress = null)
    {
        var formats = new Dictionary<string, FFmpegFormat>();
        var output = await RunCmdAsync("-formats");

        var lines = output.Split(new[] { '\r', '\n' }, StringSplitOptions.RemoveEmptyEntries)
                        .Where(l => FormatListRegex.IsMatch(l))
                        .ToList();

        // Pass 1: Quick map building
        foreach (var line in lines)
        {
            var match = FormatListRegex.Match(line);
            if (!match.Success) continue;

            bool isDemuxer = match.Groups[1].Value == "D";
            bool isMuxer = match.Groups[2].Value == "E";
            var names = match.Groups[3].Value.Split(',');
            var descr = match.Groups[4].Value;
            var primaryName = names[0];

            if (formats.TryGetValue(primaryName, out var existingFormat))
            {
                existingFormat.IsDemuxer |= isDemuxer;
                existingFormat.IsMuxer |= isMuxer;
                formats[primaryName] = existingFormat;
            }
            else
            {
                formats[primaryName] = new FFmpegFormat
                {
                    Description = descr.Trim(),
                    IsDemuxer = isDemuxer,
                    IsMuxer = isMuxer,
                    Aliases = names.Skip(1).ToArray(),
                    FileExtensions = Array.Empty<string>(),
                    Parameters = new Dictionary<string, FFmpegParameter>()
                };
            }
        }

        // Pass 2: Deep Probe with active UI feedback
        var keys = formats.Keys.ToList();
        for (int i = 0; i < keys.Count; i++)
        {
            var key = keys[i];
            // UPDATE UI HERE: This makes sure the user sees movement for every format probed
            onProgress?.Invoke(key, (double)i / keys.Count);

            var fmt = formats[key];
            string combinedDetails = "";

            if (fmt.IsMuxer) combinedDetails += await RunCmdAsync($"-h muxer={key}");
            if (fmt.IsDemuxer) combinedDetails += "\n" + await RunCmdAsync($"-h demuxer={key}");

            if (!string.IsNullOrWhiteSpace(combinedDetails) && !combinedDetails.Contains("Unknown"))
            {
                fmt.Parameters = ParseAVOptions(combinedDetails);
                var extMatch = ExtensionRegex.Match(combinedDetails);
                if (extMatch.Success)
                {
                    fmt.FileExtensions = extMatch.Groups[1].Value
                        .Split(',', StringSplitOptions.RemoveEmptyEntries)
                        .Select(e => e.Trim().TrimEnd('.'))
                        .ToArray();
                }
                formats[key] = fmt;
            }
        }

        return formats;
    }
}