using System.Diagnostics;
using System.Text.Json;

namespace FFGui.Services;

public class FFmpegMediaInfo
{
    private readonly string _ffprobePath;
    private readonly long _probeSize;
    private readonly long _analyzeDuration;

    public FFmpegMediaInfo(string ffprobePath, long probeSize = 26214400, long analyzeDuration = 120000000)
    {
        _ffprobePath = ffprobePath;
        _probeSize = probeSize;
        _analyzeDuration = analyzeDuration;
    }

    public async Task<JsonElement> GetInfoAsync(string filename)
    {
        var args = $"-probesize {_probeSize} -analyzeduration {_analyzeDuration} -v quiet -of json -show_streams -show_format \"{filename}\"";
        var psi = new ProcessStartInfo(_ffprobePath, args)
        {
            RedirectStandardOutput = true,
            UseShellExecute = false,
            CreateNoWindow = true
        };

        using var proc = Process.Start(psi);
        var json = await proc!.StandardOutput.ReadToEndAsync();
        return JsonDocument.Parse(json).RootElement;
    }

    public static string[] GetStreamDescription(JsonElement stream)
    {
        string bitrateStr = "";
        if (stream.TryGetProperty("bit_rate", out var brProp) && long.TryParse(brProp.GetString(), out var br))
        {
            bitrateStr = $", ~{br / 1000} kbps";
        }

        string codecLong = stream.TryGetProperty("codec_long_name", out var cl) ? cl.GetString() ?? "Unknown" : "Unknown";
        string type = stream.TryGetProperty("codec_type", out var t) ? t.GetString() ?? "unknown" : "unknown";

        switch (type)
        {
            case "audio":
                if (stream.TryGetProperty("sample_rate", out var sr))
                {
                    int ch = stream.TryGetProperty("channels", out var c) ? c.GetInt32() : 0;
                    return [$"(Audio) {codecLong}", $"{ch}ch, {sr.GetString() ?? "?"} Hz{bitrateStr}"];
                }
                else
                {
                    return ["(Audio) Unknown"];
                }
            case "video":
                int width = stream.TryGetProperty("width", out var w) ? w.GetInt32() : 0;
                int height = stream.TryGetProperty("height", out var h) ? h.GetInt32() : 0;
                string pixFmt = stream.TryGetProperty("pix_fmt", out var p) ? p.GetString() ?? "unknown" : "unknown";
                string fps = stream.TryGetProperty("avg_frame_rate", out var f) ? f.GetString() ?? "unknown" : "unknown";
                return [$"(Video) {codecLong}", $"{width}x{height}, {pixFmt}, {fps} FPS{bitrateStr}"];
            default:
                return [$"({type}): {codecLong}]", $"{bitrateStr}"];
        }
    }
}