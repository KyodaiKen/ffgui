namespace FFGui.Models;

using System.Globalization;
using System.Text.Json;
using FFGui.Services;
using FFGui.UI;
using YamlDotNet.Serialization;

public class Job
{
    public enum JobStatus
    {
        Pending,
        Running,
        Failed,
        Successful
    }
    public record Source
    {
        public record Stream
        {
            public record TrimSettings
            {
                //Using strings so the user's syntax can be preserved
                public string Start = "";
                public string Length = "";
                public string End = "";
            }

            public bool Active;
            public int Index;
            public bool UseHwDec;

            public string Type = "";
            public string DescriptionCodec = "";
            public string DescriptionCodecExtended = "";
            public double Duration;
            public ulong Bitrate;
            public string Template = "";
            public EncoderSettings EncoderSettings = new();

            public string Language = "";

            public List<string> Disposition = [];
            public Dictionary<string, string> Metadata = [];
            public string Delay = ""; //Using string so the user's syntax can be preserved
            public TrimSettings Trim = new();
        }

        public string FileName { get; set; } = "";
        public Dictionary<string, string> Metadata { get; set; } = [];
        [YamlIgnore]
        public string[] Format { get; set; } = [];
        [YamlIgnore]
        public string FormatDescription { get; set; } = "";
        public string Demuxer { get; set; } = "";
        public ulong Bitrate;
        public List<Stream> Streams { get; set; } = [];
    }

    [YamlIgnore]
    private string _name = "";

    public string Name
    {
        get => _name;
        set
        {
            if (_name != value)
                _isNameCustom = true;
            _name = value;
        }
    }

    public List<Source> Sources;
    public double TotalDuration;
    public string Multiplexer = "";
    public Dictionary<string, object> MuxerParameters = [];
    public Dictionary<string, string> Metadata = [];
    public string OutputDirectory = "";
    public string OutputFileName = "";

    [YamlIgnore]
    private string _ffProbePath;
    [YamlIgnore]
    private bool _isNameCustom = false;
    [YamlIgnore]
    public bool IsCurrentlyProbing { get; set; }

    [YamlIgnore]
    public JobStatus Status = JobStatus.Pending;
    [YamlIgnore]
    public string ErrorLog = "";

    // Parallel job execution
    public byte ParallelGroup = 0;

    // For Yaml Deserialization
    public Job()
    {
        Name = "";
        Sources = new List<Source>();
         // These will be set manually after loading
        _ffProbePath = "";
    }

    // When the user creates a new empty job
    public Job(string ffProbePath)
    {
        _ffProbePath = ffProbePath;
        Name = "";
        Sources = [];
        TotalDuration = 0;
    }

    public Job Clone()
    {
        return DynamicCloner.DeepClone(this) ?? new Job();
    }

    public void UpdateFrom(Job other)
    {
        DynamicCloner.UpdateProperties(this, other);
    }

    /// <summary>
    /// Adds a single file. Internal helper that performs the blocking probe.
    /// Should be run inside a Task.
    /// </summary>
    private Source ProbeSingleFile(string fileName, CancellationToken ct)
    {
        ct.ThrowIfCancellationRequested();

        var probeService = new FFmpegMediaInfo(_ffProbePath);

        // Block synchronously here since we are already in a background Task
        JsonElement root = probeService.GetInfoAsync(fileName).GetAwaiter().GetResult();

        var newSource = new Source
        {
            FileName = fileName,
            Metadata = [],
            Streams = [],
            Format = [],
            FormatDescription = ""
        };

        TimeSpan containerDuration = TimeSpan.Zero;
        if (root.TryGetProperty("format", out var format))
        {
            if (root.TryGetProperty("streams", out var streams))
            {
                foreach (var jsonStream in streams.EnumerateArray())
                {
                    var s = new Source.Stream();
                    s.Index = jsonStream.TryGetProperty("index", out var idx) ? idx.GetInt32() : 0;
                    s.Type = jsonStream.TryGetProperty("codec_type", out var type) ? type.GetString() ?? "unknown" : "unknown";
                    var descr = FFmpegMediaInfo.GetStreamDescription(jsonStream);
                    s.DescriptionCodec = descr[0];
                    s.DescriptionCodecExtended = descr[1];

                    s.Active = true;
                    s.UseHwDec = false;
                    s.Template = "Copy";
                    s.EncoderSettings = new() { Encoder = "copy" };

                    TimeSpan streamDur = TimeSpan.Zero;
                    if (jsonStream.TryGetProperty("duration", out var sDurProp))
                        streamDur = ParseTime(sDurProp.GetString());

                    s.Duration = (streamDur > TimeSpan.Zero ? streamDur : containerDuration).TotalSeconds;
                    s.Bitrate = ulong.TryParse(jsonStream.TryGetProperty("bit_rate", out var sbr) ? sbr.GetString() : "0", out ulong ubr) ? ubr : 0;

                    s.Metadata = new Dictionary<string, string>();
                    s.Language = "und";

                    if (jsonStream.TryGetProperty("tags", out var stags))
                    {
                        foreach (var tag in stags.EnumerateObject())
                        {
                            s.Metadata[tag.Name] = tag.Value.GetString() ?? "";
                            if (tag.Name.ToLower() == "language") s.Language = tag.Value.GetString() ?? "und";
                        }
                    }

                    s.Disposition = new List<string>();
                    if (jsonStream.TryGetProperty("disposition", out var disp))
                    {
                        foreach (var d in disp.EnumerateObject())
                        {
                            if (d.Value.GetInt32() == 1) s.Disposition.Add(d.Name);
                        }
                    }

                    newSource.Streams.Add(s);
                }
            }

            if (format.TryGetProperty("duration", out var durProp))
                containerDuration = ParseTime(durProp.GetString());
            newSource.Format = (format.TryGetProperty("format_name", out var fmtnm) ? fmtnm.GetString() ?? "" : "").Split(",");
            newSource.FormatDescription = format.TryGetProperty("format_long_name", out var fmtln) ? fmtln.GetString() ?? "" : "";
            newSource.Demuxer = newSource.Format[0];
            newSource.Bitrate = ulong.TryParse(format.TryGetProperty("bit_rate", out var fbr) ? fbr.GetString() : "0", out ulong ufbr) ? ufbr : 0;

            //Loop through format tags and add metadata:
            if (format.TryGetProperty("tags", out var tags))
            {
                foreach (var tag in tags.EnumerateObject())
                {
                    string tagValue = tag.Value.GetString() ?? "";
                    newSource.Metadata[tag.Name] = tagValue;

                    // Handle bundled demuxers
                    switch (newSource.Demuxer)
                    {
                        case "mov":
                            // Identification logic for ISO BMFF family
                            if (tag.Name == "major_brand")
                            {
                                newSource.Demuxer = tagValue.Trim().ToLower() switch
                                {
                                    "isom" or "mp41" or "mp42"  => "mp4",
                                    "qt"                        => "mov",
                                    "m4a" or "m4b" or "m4p"     => "m4a",
                                    "3gp4" or "3gp5" or "3gp6"  => "3gp",
                                    "3g2a" or "3g2"             => "3g2",
                                    "mjp2"                      => "mj2",
                                    _                           => newSource.Demuxer
                                };
                            }
                            break;

                        case "matroska":
                        case "mkv":
                            // Check if it's actually WebM
                            if (newSource.FormatDescription.Contains("WebM", StringComparison.OrdinalIgnoreCase))
                                newSource.Demuxer = "webm";
                            break;

                        case "asf":
                            // Differentiate WMV vs WMA
                            bool hasVideo = newSource.Streams.Any(s => s.Type == "video");
                            newSource.Demuxer = hasVideo ? "wmv" : "wma";
                            break;
                    }
                }
            }
        }

        return newSource;
    }

    /// <summary>
    /// Handles adding files with a smart progress window trigger.
    /// Uses IsCurrentlyProbing to prevent multiple simultaneous analysis tasks.
    /// </summary>
    public async Task AddSourceFilesAsync(List<string> fileNames)
    {
        // 1. Race condition check
        if (IsCurrentlyProbing)
        {
            Console.WriteLine("Analysis already in progress. Ignoring request.");
            return;
        }

        if (fileNames == null || fileNames.Count == 0) return;

        IsCurrentlyProbing = true;

        if ((string.IsNullOrEmpty(Name) || Sources.Count == 0) && !_isNameCustom)
            _name = Path.GetFileName(fileNames[0]);

        using var cts = new CancellationTokenSource();
        ProgressWindow? progWin = null;
        bool isWindowShown = false;

        // 2. Start the timer to show window after 2 seconds
        var timerTask = Task.Delay(500, cts.Token).ContinueWith(t =>
        {
            if (t.IsCanceled) return;

            GLib.Functions.IdleAdd(0, () =>
            {
                if (cts.IsCancellationRequested) return false;

                progWin = new ProgressWindow();
                progWin.OnCancelRequested += (s, e) => cts.Cancel();
                progWin.Show();
                isWindowShown = true;
                return false;
            });
        });

        try
        {
            // 3. Run the probing loop in background
            await Task.Run(() =>
            {
                int total = fileNames.Count;
                for (int i = 0; i < total; i++)
                {
                    cts.Token.ThrowIfCancellationRequested();

                    string file = fileNames[i];

                    if (isWindowShown && progWin != null)
                    {
                        double fraction = (double)i / total;
                        string status = $"Analyzing {i + 1}/{total}: {Path.GetFileName(file)}";
                        GLib.Functions.IdleAdd(0, () =>
                        {
                            progWin?.UpdateStatus(status, fraction);
                            return false;
                        });
                    }

                    try
                    {
                        var source = ProbeSingleFile(file, cts.Token);

                        // Since we are inside Task.Run, we modify the Job instance directly.
                        // Class reference semantics ensure this updates the UI's bound object.
                        Sources.Add(source);

                        if (source.Streams.Count > 0 && source.Streams[0].Duration > TotalDuration)
                            TotalDuration = source.Streams[0].Duration;
                    }
                    catch (Exception ex)
                    {
                        Console.WriteLine($"Failed to probe {file}: {ex.Message}");
                    }
                }
            }, cts.Token);
        }
        catch (OperationCanceledException)
        {
            Console.WriteLine("Import cancelled by user.");
        }
        finally
        {
            // 4. Cleanup and reset the gatekeeper
            cts.Cancel();
            IsCurrentlyProbing = false;

            if (isWindowShown)
            {
                GLib.Functions.IdleAdd(0, () =>
                {
                    progWin?.Destroy();
                    return false;
                });
            }
        }
    }

    // Single file wrapper for compatibility
    public async Task AddSourceFileAsync(string fileName)
    {
        await AddSourceFilesAsync(new List<string> { fileName });
    }

    private static TimeSpan ParseTime(string? input)
    {
        if (string.IsNullOrEmpty(input)) return TimeSpan.Zero;
        if (double.TryParse(input, NumberStyles.Any, CultureInfo.InvariantCulture, out double seconds))
        {
            return TimeSpan.FromSeconds(seconds);
        }
        return TimeSpan.Zero;
    }

    public void SetProbePath(string path) => _ffProbePath = path;
}