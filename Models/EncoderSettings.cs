namespace FFGui.Models;

public struct EncoderSettings
{
    public struct FilterSettings
    {
        public string FilterName { get; set; }
        public List<string>? ComplexInputConnections { get; set; }
        public List<string>? ComplexOutputConnections { get; set; }
        public Dictionary<string, object> Parameters { get; set; }
    }

    public string Encoder { get; set; }
    public Dictionary<string, object>? Parameters { get; set; }
    public bool UsesComplexFilters { get; set; }
    public List<FilterSettings>? Filters { get; set; }
}
