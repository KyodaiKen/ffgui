namespace FFGui.Services;

using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Runtime.InteropServices;
using GLib;
using Models;

public static class FFmpegCmdCompiler
{
    private static readonly HashSet<string> GlobalOptions = new()
    {
        "y", "n", "stats", "loglevel", "threads", "f", "t", "to", "ss", "re", "discard", "benchmark"
    };

    private static readonly Dictionary<string, string> TypeMap = new()
    {
        { "video", "v" },
        { "audio", "a" },
        { "subtitle", "s" },
        { "data", "d" },
        { "attachment", "t" }
    };

    public static string[] CompileFFmpegCmd(this Job job, FFmpegCache ffmpegCache, bool forPreview = false)
    {
        var cmd = new List<string>
        {
            "-y",
            "-hide_banner"
        };

        // --- PHASE 1: INPUTS & DELAY HANDLING ---
        var inputGroups = new List<InputGroup>();

        for (int srcIdx = 0; srcIdx < job.Sources.Count; srcIdx++)
        {
            var source = job.Sources[srcIdx];
            var activeStreams = source.Streams.Where(s => s.Active).ToList();
            if (!activeStreams.Any()) continue;

            var delayGroups = activeStreams.GroupBy(s => s.Delay ?? "0");

            foreach (var group in delayGroups)
            {
                string delayVal = group.Key;
                if (ParseDelayToSeconds(delayVal) > 0)
                {
                    cmd.Add("-itsoffset");
                    cmd.Add(delayVal);
                }

                cmd.Add("-i");
                cmd.Add(source.FileName);

                inputGroups.Add(new InputGroup
                {
                    OriginalSourceIdx = srcIdx,
                    Delay = delayVal,
                    StreamIndices = group.Select(s => s.Index).ToList()
                });
            }
        }

        // --- PHASE 2: STREAM MAPPING & ENCODING ---
        var typeCounters = new Dictionary<string, int> { { "video", 0 }, { "audio", 0 }, { "subtitle", 0 } };

        foreach (var streamInfo in job.Sources.SelectMany((src, srcIdx) => src.Streams.Where(s => s.Active).Select(s => new { src, srcIdx, stream = s })))
        {
            var stream = streamInfo.stream;
            string sType = (stream.Type ?? "video").ToLower();
            string tChar = TypeMap.GetValueOrDefault(sType, "v");
            int outIdx = typeCounters.GetValueOrDefault(sType, 0);
            string specifier = $":{tChar}:{outIdx}";

            int ffmpegInputIdx = GetInputIdx(streamInfo.srcIdx, stream.Index, stream.Delay, inputGroups);
            cmd.Add("-map");
            cmd.Add($"{ffmpegInputIdx}:{stream.Index}");

            if (!string.IsNullOrEmpty(stream.Language))
            {
                cmd.Add($"-metadata:s{specifier}");
                cmd.Add($"language={stream.Language}");
            }

            if (stream.Metadata != null)
            {
                foreach (var kv in stream.Metadata)
                {
                    cmd.Add($"-metadata:s{specifier}");
                    cmd.Add($"{kv.Key}={kv.Value}");
                }
            }

            if (stream.Trim is Job.Source.Stream.TrimSettings trim)
            {
                if (!string.IsNullOrEmpty(trim.Start)) { cmd.Add($"-ss{specifier}"); cmd.Add(trim.Start); }
                if (!string.IsNullOrEmpty(trim.Length)) { cmd.Add($"-t{specifier}"); cmd.Add(trim.Length); }
                else if (!string.IsNullOrEmpty(trim.End)) { cmd.Add($"-to{specifier}"); cmd.Add(trim.End); }
            }

            if (forPreview)
            {
                bool hasFilters = stream.EncoderSettings.Filters.Any();
                if (hasFilters)
                {
                    if (sType == "video") cmd.AddRange(new[] { $"-c{specifier}", "rawvideo" });
                    else if (sType == "audio") cmd.AddRange(new[] { $"-c{specifier}", "pcm_s16le" });
                    else cmd.AddRange(new[] { $"-c{specifier}", "copy" });
                }
                else cmd.AddRange(new[] { $"-c{specifier}", "copy" });
            }
            else
            {
                cmd.Add($"-c{specifier}");
                cmd.Add(string.IsNullOrEmpty(stream.EncoderSettings.Encoder) ? "copy" : stream.EncoderSettings.Encoder);

                if (stream.EncoderSettings.Parameters != null)
                {
                    foreach (var param in stream.EncoderSettings.Parameters)
                    {
                        string val = param.Value?.ToString() ?? "";
                        if (val.Equals("true", StringComparison.OrdinalIgnoreCase)) val = "1";
                        if (val.Equals("false", StringComparison.OrdinalIgnoreCase)) val = "0";

                        if (GlobalOptions.Contains(param.Key)) cmd.AddRange(new[] { $"-{param.Key}", val });
                        else cmd.AddRange(new[] { $"-{param.Key}{specifier}", val });
                    }
                }
            }

            if (stream.EncoderSettings.Filters?.Count > 0)
            {
                string filterStr = BuildFilterString(stream.EncoderSettings.Filters);
                if (!string.IsNullOrEmpty(filterStr))
                {
                    cmd.Add($"-filter{specifier}");
                    cmd.Add(filterStr);
                }
            }

            if (stream.Disposition != null && stream.Disposition.Any())
            {
                cmd.Add($"-disposition{specifier}");
                cmd.Add(string.Join("+", stream.Disposition));
            }

            typeCounters[sType] = outIdx + 1;
        }

        // --- PHASE 3: OUTPUT ---
        if (forPreview)
        {
            cmd.AddRange(new[] { "-f", "nut", "-" });
        }
        else
        {
            cmd.AddRange(new[] { "-progress", "pipe:1" });

            // Multiplexer
            string muxer = job.Multiplexer;
            if (string.IsNullOrEmpty(muxer) && job.Sources.Count > 0)
                muxer = job.Sources[0].Demuxer;

            if (!string.IsNullOrEmpty(muxer))
            {
                cmd.Add("-f");
                cmd.Add(muxer);
            }

            if (job.MuxerParameters != null)
            {
                foreach (var mp in job.MuxerParameters)
                {
                    cmd.Add($"-{mp.Key}");
                    cmd.Add(mp.Value?.ToString() ?? "");
                }
            }

            // Path Fallback & File Resolution
            string resolvedPath = ResolveOutputPath(job, ffmpegCache, muxer);
            if (!string.IsNullOrEmpty(resolvedPath))
            {
                cmd.Add(resolvedPath);
            }
        }

        return cmd.ToArray();
    }

    private static string ResolveOutputPath(Job job, FFmpegCache ffmpegCache, string muxer)
    {
        if (job.Sources.Count == 0) return "";

        string dir = job.OutputDirectory;
        if (string.IsNullOrEmpty(dir))
            dir = Path.GetDirectoryName(job.Sources[0].FileName) ?? "";

        string fileName = job.OutputFileName;
        string extension = "";

        // Determine extension from muxer if file name is empty or lacks extension
        // Note: _app.Cache is assumed to be accessible in your context
        if (!string.IsNullOrEmpty(muxer))
            extension = ffmpegCache.Formats[muxer].FileExtensions[0];

        if (string.IsNullOrEmpty(fileName))
        {
            fileName = Path.GetFileNameWithoutExtension(job.Sources[0].FileName);
        }
        else if (Path.HasExtension(fileName))
        {
            extension = Path.GetExtension(fileName);
            fileName = Path.GetFileNameWithoutExtension(fileName);
        }

        if (!extension.StartsWith(".")) extension = "." + extension;

        string stem = Path.Combine(dir, fileName);
        string finalPath = stem + extension;
        ulong counter = 0;

        while (File.Exists(finalPath))
        {
            counter++;
            finalPath = $"{stem}{counter}{extension}";
        }

        return finalPath;
    }

    public static string[] CompileFFmpegPreviewCmd(this Job job)
    {
        string hwaccel = RuntimeInformation.IsOSPlatform(OSPlatform.OSX) ? "metal" : "vulkan";
        return ["-hwaccel", hwaccel, "-"];
    }

    private static string BuildFilterString(List<EncoderSettings.FilterSettings> filters)
    {
        return string.Join(",", filters.Select(f =>
        {
            if (f.Parameters == null || f.Parameters.Count == 0)
                return f.FilterName;

            var paramStrings = f.Parameters.Select(p =>
            {
                string formattedValue = FormatValue(p.Value);
                return $"{p.Key}={formattedValue}";
            });

            string @params = string.Join(":", paramStrings);
            return $"{f.FilterName}={@params}";
        }));
    }

    private static string FormatValue(object value)
    {
        return value switch
        {
            // Handle nested dictionaries (e.g., for complex filters like 'drawtext' or 'metadata')
            IDictionary<string, object> dict =>
                string.Join(":", dict.Select(kvp => $"{kvp.Key}={FormatValue(kvp.Value)}")),

            // Handle lists (e.g., for filters that take multiple flags or paths)
            IEnumerable<string> list =>
                string.Join("|", list),

            // Standard numeric or string values
            _ => value?.ToString() ?? ""
        };
    }

    private static int GetInputIdx(int sourceIdx, int streamIdx, string? delay, List<InputGroup> inputGroups)
    {
        string normalizedDelay = delay ?? "0";
        for (int i = 0; i < inputGroups.Count; i++)
        {
            var group = inputGroups[i];
            if (group.OriginalSourceIdx == sourceIdx && group.Delay == normalizedDelay)
            {
                if (group.StreamIndices.Contains(streamIdx)) return i;
            }
        }
        return 0;
    }

    private class InputGroup
    {
        public int OriginalSourceIdx { get; set; }
        public string Delay { get; set; } = "0";
        public List<int> StreamIndices { get; set; } = new();
    }

    private static double ParseDelayToSeconds(string? delay)
    {
        if (string.IsNullOrWhiteSpace(delay)) return 0;
        if (double.TryParse(delay, System.Globalization.NumberStyles.Any, System.Globalization.CultureInfo.InvariantCulture, out double sec)) 
            return sec;
        if (System.TimeSpan.TryParse(delay, out System.TimeSpan ts)) 
            return ts.TotalSeconds;
        return 0;
    }
}