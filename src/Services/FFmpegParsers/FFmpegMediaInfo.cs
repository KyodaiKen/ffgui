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

        string codecLong = stream.GetProperty("codec_long_name").GetString() ?? "Unknown";
        string type = stream.GetProperty("codec_type").GetString() ?? "unknown";

        switch (type)
        {
            case "audio":
                string sr = stream.GetProperty("sample_rate").GetString() ?? "?";
                int ch = stream.TryGetProperty("channels", out var c) ? c.GetInt32() : 0;
                return [$"(Audio) {codecLong}", $"{ch}ch, {sr} Hz{bitrateStr}"];
            case "video":
                int width = stream.GetProperty("width").GetInt32();
                int height = stream.GetProperty("height").GetInt32();
                string pixFmt = stream.GetProperty("pix_fmt").GetString() ?? "unknown";
                string fps = stream.GetProperty("avg_frame_rate").GetString() ?? "0";
                return [$"(Video) {codecLong}", $"{width}x{height}, {pixFmt}, {fps} FPS{bitrateStr}"];
            default:
                return [$"({type}): {codecLong}]", $"{bitrateStr}"];
        }
    }
}