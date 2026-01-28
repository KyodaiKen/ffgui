namespace FFGui.Models;

public struct Job
{
    public struct Source
    {
        public struct Stream
        {
            public struct TrimSettings
            {
                public TimeSpan Start { get; set; }
                public TimeSpan Length { get; set; }
                public TimeSpan End { get; set; }
            }

            public bool Active { get; set; }
            public int Index { get; set; }
            public int FileId { get; set; }
            public string Type { get; set; }
            public string Description { get; set; }
            public TimeSpan Duration { get; set; }
            public string Template { get; set; }
            public EncoderSettings EncoderSettings { get; set; }
            public string Language { get; set; }
            public List<string>? Disposition { get; set; }
            public Dictionary<string, string>? Metadata { get; set; }
            public TrimSettings? Trim { get; set; }
        }

        public List<string>? Files { get; set; }
        public List<Stream>? Streams { get; set; }
        public TimeSpan? SourceDelay { get; set; }
    }

    public struct OutputSettings
    {
        public string Directory { get; set; }
        public string FileName { get; set; }
        public string ContainerFormat { get; set; } //Muxer
        public Dictionary<string, object>? ContainerParameters { get; set; }
    }

    public string Name { get; set; }
    public List<Source> Sources { get; set; }
    public TimeSpan TotalDuration { get; set; }
}
