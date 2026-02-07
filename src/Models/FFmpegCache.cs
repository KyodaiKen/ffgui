using MemoryPack;

namespace FFGui.Models;

[MemoryPackable]
[MemoryPackUnion(0, typeof(FFmpegValueLong))]
[MemoryPackUnion(1, typeof(FFmpegValueDouble))]
[MemoryPackUnion(2, typeof(FFmpegValueString))]
public partial interface IFFmpegValue { }

[MemoryPackable] public partial record FFmpegValueLong(long Value) : IFFmpegValue;
[MemoryPackable] public partial record FFmpegValueDouble(double Value) : IFFmpegValue;
[MemoryPackable] public partial record FFmpegValueString(string Value) : IFFmpegValue;

[MemoryPackable]
public partial record FFmpegCache
{
    public int CacheVersion;
    public string FFmpegVersionHeader = "";
    public FFmpegGlobalParameters Globals = new();
    public Dictionary<string, FFmpegCodec> Codecs = [];
    public Dictionary<string, FFmpegFormat> Formats = [];
    public Dictionary<string, FFmpegPixelFormat> PixelFormats = [];
    public Dictionary<string, FFmpegFilter> Filters = [];

    public async Task SaveToFileAsync(string path)
    {
        byte[] bin = MemoryPackSerializer.Serialize(this);
        await File.WriteAllBytesAsync(path, bin);
    }

    public static FFmpegCache LoadFromFile(string path)
    {
        byte[] bin = File.ReadAllBytes(path);
        var cache = MemoryPackSerializer.Deserialize<FFmpegCache>(bin);
        return cache ?? throw new InvalidDataException("Failed to deserialize FFmpegCache.");
    }
}

[MemoryPackable]
public partial record FFmpegParameter
{
    public string Type = "";
    public string Description = "";
    public FFmpegContext Context = new();
    public IFFmpegValue? Min;
    public IFFmpegValue? Max;
    public IFFmpegValue? Default;
    public Dictionary<string, FFmpegOption>? Options;
}

[MemoryPackable]
public partial record FFmpegGlobalParameters
{
    public Dictionary<string, FFmpegParameter> Video = [];
    public Dictionary<string, FFmpegParameter> Audio = [];
    public Dictionary<string, FFmpegParameter> Subtitle = [];
    public Dictionary<string, FFmpegParameter> PerStream = [];
}

[MemoryPackable]
public partial record FFmpegPixelFormat
{
    public int NumComponents;
    public int BitsPerPixel;
    public int[] BitsPerComponent = [];
}

[MemoryPackable]
public partial record FFmpegFilter
{
    public string Description = "";
    public bool IsDynamic;
    public bool IsComplex;
    public string[] Inputs = [];
    public string[] Outputs = [];
    public FFmpegFilterFlags Flags = new();
    public Dictionary<string, FFmpegParameter> Parameters = [];
}

[MemoryPackable]
public partial record FFmpegFormat
{
    public string[] Aliases = [];
    public string[] FileExtensions = [];
    public string Description = "";
    public bool IsMuxer;
    public bool IsDemuxer;
    public Dictionary<string, FFmpegParameter> Parameters = [];
}

[MemoryPackable]
public partial record FFmpegOption
{
    public IFFmpegValue? Value;
    public string Description = "";
    public FFmpegContext Context = new();
}

[MemoryPackable]
public partial record FFmpegContext
{
    public bool Encoding;
    public bool Decoding;
    public bool Filtering;
    public bool Video;
    public bool Audio;
    public bool Subtitle;
    public bool Timeline;
    public bool Runtime;
}

[MemoryPackable]
public partial record FFmpegCodecFlags
{
    public bool Encoder;
    public bool Decoder;
    public bool Video;
    public bool Audio;
    public bool Subtitle;
    public bool Lossy;
}

[MemoryPackable]
public partial record FFmpegFilterFlags
{
    public bool Timeline;
    public bool SliceThreading;
    public bool CommandSupport;
}

[MemoryPackable]
public partial record FFmpegPixelFormatFlags
{
    public bool InputSupported;
    public bool OutputSupported;
    public bool HwAccel;
    public bool Paletted;
    public bool Bitstream;
}

[MemoryPackable]
public partial record FFmpegCodec
{
    public string Description = "";
    public FFmpegCodecFlags Flags = new();
    public Dictionary<string, FFmpegParameter> Parameters = [];
}