namespace FFGui.Models;

public record EncoderSettings
{
    public record FilterSettings
    {
        public string FilterName = "";
        public List<string> ComplexInputConnections = [];
        public List<string> ComplexOutputConnections = [];
        public Dictionary<string, object> Parameters = [];
    }

    public string Encoder = "libsvtav1";
    public Dictionary<string, object>? Parameters;
    public bool UsesComplexFilters;
    public List<FilterSettings> Filters = [];
}
