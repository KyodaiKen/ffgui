using YamlDotNet.Serialization;

namespace FFGui.Models;

public abstract record Template
{
    [YamlIgnore]
    public string Name = "";
    public string Description = "";
}
public record TranscodingTemplate : Template
{
    public string Type = "video";
    public EncoderSettings EncoderSettings = new();
}

public record ContainerTemplate : Template
{
    public string Muxer = "mp4";
    public Dictionary<string, object> Parameters = [];
}

public record FilterTemplate : Template
{
    public string Type = "video";
    public bool ComplexFilters = false;
    public List<EncoderSettings.FilterSettings> Filters = [];
}