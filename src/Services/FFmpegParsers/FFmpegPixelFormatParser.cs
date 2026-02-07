using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.RegularExpressions;
using System.Threading.Tasks;
using FFGui.Models;

namespace FFGui.Services;

public class FFmpegPixelFormatParser : FFmpegBaseParser
{
    // Regex matches: Flags (5 chars), Name, Components, Bits-per-pixel, and Bit-depths (e.g., 8-8-8)
    private static readonly Regex PixFmtRegex = new(@"^([IOHBP\.]{5})\s+([\w-]+)\s+(\d+)\s+(\d+)\s+([\d-]+)$", RegexOptions.Compiled);

    public FFmpegPixelFormatParser(string ffmpegPath = "ffmpeg") : base(ffmpegPath) { }

    public async Task<Dictionary<string, FFmpegPixelFormat>> ParseAllAsync(ProgressCallback? onProgress = null)
    {
        var pixFmts = new Dictionary<string, FFmpegPixelFormat>();
        var output = await RunCmdAsync("-pix_fmts");
        
        var lines = output.Split(new[] { '\r', '\n' }, StringSplitOptions.RemoveEmptyEntries);

        // Logic from Python: Start parsing only after the header separator "-----"
        bool startParsing = false;

        for (int i = 0; i < lines.Length; i++)
        {
            string line = lines[i];

            if (line.Contains("-----"))
            {
                startParsing = true;
                continue;
            }

            if (!startParsing) continue;

            var match = PixFmtRegex.Match(line);
            if (!match.Success) continue;

            string flags = match.Groups[1].Value;
            string name = match.Groups[2].Value;

            onProgress?.Invoke(name, (double)i / lines.Length);

            // Parse depths from string like "8-8-8" into int array [8, 8, 8]
            int[] componentDepths = match.Groups[5].Value
                .Split('-', StringSplitOptions.RemoveEmptyEntries)
                .Select(d => int.TryParse(d, out int val) ? val : 0)
                .ToArray();

            pixFmts[name] = new FFmpegPixelFormat
            {
                NumComponents = int.Parse(match.Groups[3].Value),
                BitsPerPixel = int.Parse(match.Groups[4].Value),
                BitsPerComponent = componentDepths
            };
        }

        return pixFmts;
    }
}