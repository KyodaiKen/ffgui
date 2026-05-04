using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.RegularExpressions;
using System.Threading.Tasks;
using FFGui.Models;

namespace FFGui.Services;

public class FFmpegCodecParser : FFmpegBaseParser
{
    // Regex for -codecs list: Flags (6 chars), Name, and Description
    private static readonly Regex CodecListRegex = new(@"^\s([D.E.VASDT.ILS.]{6})\s+([\w-]+)\s+(.*)$", RegexOptions.Compiled);

    // Regex for bracketed handlers: (decoders: name1 name2) or (encoders: name1)
    private static readonly Regex BracketsRegex = new(@"\((decoders|encoders):\s*([^)]+)\)", RegexOptions.Compiled);

    public FFmpegCodecParser(string ffmpegPath = "ffmpeg") : base(ffmpegPath) { }

    public async Task<Dictionary<string, FFmpegCodec>> ParseAllAsync(ProgressCallback? onProgress = null)
    {
        var codecMap = new Dictionary<string, FFmpegCodec>();
        var rogueNames = new HashSet<string>();

        var output = await RunCmdAsync("-codecs");
        var lines = output.Split(new[] { "\r\n", "\r", "\n" }, StringSplitOptions.RemoveEmptyEntries);

        // --- First Pass: Build the map and identify parents (Rogue Names) ---
        foreach (var line in lines)
        {
            var match = CodecListRegex.Match(line);
            if (!match.Success) continue;

            string flagsRaw = match.Groups[1].Value;
            string mainName = match.Groups[2].Value;
            string descrFull = match.Groups[3].Value;

            UpdateOrCreateCodec(codecMap, mainName, descrFull.Split('(')[0].Trim(), flagsRaw, flagsRaw[0] == 'D', flagsRaw[1] == 'E');

            var handlers = ParseBracketedHandlers(descrFull);

            if (handlers.Any())
            {
                // Logic from Python: If brackets exist, process specific handlers
                foreach (var h in handlers)
                {
                    UpdateOrCreateCodec(codecMap, h.Name, descrFull.Split('(')[0].Trim(), flagsRaw, h.IsDecoder, h.IsEncoder);
                }

                // If the main name (e.g. 'av1') isn't in the handler list, it's a rogue parent
                if (!handlers.Any(h => h.Name == mainName))
                {
                    rogueNames.Add(mainName);
                }
            }
        }

        // Remove any generic parents that were flagged
        foreach (var rogue in rogueNames)
        {
            if (codecMap.TryGetValue(rogue, out var c) && (c.Flags.Encoder || c.Flags.Decoder))
                continue;
            codecMap.Remove(rogue);
        }

        // --- Second Pass: Deep probe for AVOptions ---
        var codecNames = codecMap.Keys.ToList();
        for (int i = 0; i < codecNames.Count; i++)
        {
            var name = codecNames[i];
            var codec = codecMap[name];
            onProgress?.Invoke(name, (double)i / codecNames.Count);

            await ProbeHelp(name, codec, true);  // Probe Encoder
            await ProbeHelp(name, codec, false); // Probe Decoder

            // If we are dealing with a hardware codec, check if the hardware is actually supported
            if (((string[])["vaapi", "amf", "qsv", "nvenc"]).Any(k => name.Contains(k)))
            {
                await ProbeHwCodec(name, codec);
            }

            codecMap[name] = codec; // Make sure persistence if FFmpegCodec is a struct
        }

        return codecMap;
    }

    private async Task ProbeHelp(string name, FFmpegCodec codec, bool isEncoder)
    {
        if (isEncoder && !codec.Flags.Encoder) return;
        if (!isEncoder && !codec.Flags.Decoder) return;

        string helpType = isEncoder ? "encoder" : "decoder";
        string helpOutput = await RunCmdAsync($"-h {helpType}={name}");

        if (string.IsNullOrWhiteSpace(helpOutput) || helpOutput.Contains("Unknown")) return;

        var newParams = ParseAVOptions(helpOutput);
        foreach (var kvp in newParams)
        {
            if (!codec.Parameters.TryGetValue(kvp.Key, out var existingParam))
            {
                // New parameter found in this probe
                codec.Parameters[kvp.Key] = kvp.Value;
            }
            else
            {
                // MIX the contexts and merge options.
                // If Encoder says 'Encoding: true' and Decoder says 'Decoding: true', the result is BOTH.
                existingParam.Context.Encoding |= kvp.Value.Context.Encoding;
                existingParam.Context.Decoding |= kvp.Value.Context.Decoding;
                existingParam.Context.Video |= kvp.Value.Context.Video;
                existingParam.Context.Audio |= kvp.Value.Context.Audio;

                if (kvp.Value.Options != null)
                {
                    existingParam.Options ??= new Dictionary<string, FFmpegOption>();
                    foreach (var opt in kvp.Value.Options)
                    {
                        existingParam.Options[opt.Key] = opt.Value;
                    }
                }
            }
        }
    }

    private async Task ProbeHwCodec(string name, FFmpegCodec codec)
    {
        // Path.GetTempPath() automatically resolves to:
        // Windows: %TMP% or %TEMP% (e.g., C:\Users\User\AppData\Local\Temp\)
        // Linux: /tmp/
        // macOS: /var/folders/...
        string tempFile = Path.Combine(Path.GetTempPath(), $"ffgui_probe_{Guid.NewGuid():N}.mp4");

        try
        {
            bool hwEncodeSuccess = false;

            // --- 1. HARDWARE ENCODING TEST ---
            if (codec.Flags.Encoder)
            {
                // Note: -y automatically overwrites the file if it exists.
                string hwEncodeArgs = $"-y -f lavfi -i color=c=blue:s=1280x720:r=24 -t 1 -c:v {name} \"{tempFile}\"";

                try
                {
                    await RunCmdAsync(hwEncodeArgs);

                    // Verify the file was actually created and is not empty
                    if (File.Exists(tempFile) && new FileInfo(tempFile).Length > 0)
                    {
                        hwEncodeSuccess = true;
                        codec.Flags.HardwareAvailable = true;
                    }
                }
                catch
                {
                    // RunCmdAsync likely threw an exception on non-zero exit code
                    hwEncodeSuccess = false;
                }
            }

            // --- 2. CPU ENCODING FALLBACK ---
            // If HW encoding failed (or wasn't attempted because this is only a decoder), 
            // we MUST generate the file via CPU so the decode test has a valid input file.
            if (!File.Exists(tempFile) || new FileInfo(tempFile).Length == 0)
            {
                string cpuEncodeArgs = $"-y -f lavfi -i color=c=blue:s=1280x720:r=24 -t 1 -c:v libx264 \"{tempFile}\"";

                try
                {
                    await RunCmdAsync(cpuEncodeArgs);
                }
                catch
                {
                    // If CPU encoding fails, FFmpeg is likely completely broken or missing. 
                    // We cannot test decoding.
                    return;
                }
            }

            // Ensure the file is ready before proceeding
            if (!File.Exists(tempFile)) return;

            // --- 3. HARDWARE DECODING TEST ---
            if (codec.Flags.Decoder)
            {
                // Use -hwaccel auto and explicitly test the specific decoder name
                // Outputting to -f null - prevents disk write bottlenecks
                string hwDecodeArgs = $"-hwaccel auto -c:v {name} -i \"{tempFile}\" -f null -";

                try
                {
                    string decodeOutput = await RunCmdAsync(hwDecodeArgs);

                    // Some implementations of RunCmdAsync might return an error string instead of throwing.
                    // Check if the output indicates a missing decoder or initialization failure.
                    if (string.IsNullOrWhiteSpace(decodeOutput) || decodeOutput.Contains("Unknown decoder"))
                    {
                        if (!codec.Flags.Encoder || !hwEncodeSuccess)
                        {
                            codec.Flags.HardwareAvailable = false;
                        }
                    }
                    else
                    {
                        codec.Flags.HardwareAvailable = true;
                    }
                }
                catch
                {
                    // If decode fails, only set to false if the encode phase didn't already prove HW availability
                    if (!codec.Flags.Encoder || !hwEncodeSuccess)
                    {
                        codec.Flags.HardwareAvailable = false;
                    }
                }
            }
        }
        finally
        {
            // --- 4. CLEANUP ---
            if (File.Exists(tempFile))
            {
                try
                {
                    File.Delete(tempFile);
                }
                catch
                {
                    // Suppress deletion errors (e.g., if the file is momentarily locked by the OS)
                    // in a background probe method to prevent app crashes.
                }
            }
        }
    }

    private void UpdateOrCreateCodec(Dictionary<string, FFmpegCodec> map, string name, string descr, string flags, bool isDec, bool isEnc)
    {
        if (!map.TryGetValue(name, out var existing))
        {
            map[name] = new FFmpegCodec
            {
                Description = descr,
                Flags = new FFmpegCodecFlags
                {
                    Decoder = isDec,
                    Encoder = isEnc,
                    Video = flags[2] == 'V',
                    Audio = flags[2] == 'A',
                    Subtitle = flags[2] == 'S',
                    Lossy = flags[4] == 'L'
                },
                Parameters = new Dictionary<string, FFmpegParameter>()
            };
        }
        else
        {
            // Use a temporary variable to modify the flags
            var f = existing.Flags;

            // MIX the flags: if it was true before, keep it true.
            f.Decoder |= isDec;
            f.Encoder |= isEnc;

            // Make sure media types are mixed as well (some codecs support multiple)
            f.Video |= flags[2] == 'V';
            f.Audio |= flags[2] == 'A';
            f.Subtitle |= flags[2] == 'S';
            f.Lossy |= flags[4] == 'L';

            existing.Flags = f;
            // No need to re-assign to map if FFmpegCodec is a class (reference type),
            // but it doesn't hurt.
            map[name] = existing;
        }
    }

    private List<(string Name, bool IsDecoder, bool IsEncoder)> ParseBracketedHandlers(string descr)
    {
        var results = new List<(string, bool, bool)>();
        var matches = BracketsRegex.Matches(descr);
        foreach (Match m in matches)
        {
            bool isDec = m.Groups[1].Value == "decoders";
            bool isEnc = m.Groups[1].Value == "encoders";
            var names = m.Groups[2].Value.Split(new[] { ' ' }, StringSplitOptions.RemoveEmptyEntries);
            foreach (var n in names)
                results.Add((n, isDec, isEnc));
        }
        return results;
    }
}