using YamlDotNet.Core;
using YamlDotNet.Core.Events;
using YamlDotNet.Serialization;
using YamlDotNet.Serialization.NamingConventions;
using System.Globalization;

namespace FFGui.Models;

public static class YamlExtensions
{
    private static readonly ISerializer _serializer = new SerializerBuilder()
        .WithNamingConvention(UnderscoredNamingConvention.Instance)
        .WithTypeConverter(new TimeSpanToDoubleConverter())
        .ConfigureDefaultValuesHandling(DefaultValuesHandling.OmitNull | DefaultValuesHandling.OmitEmptyCollections)
        .Build();

    private static readonly IDeserializer _deserializer = new DeserializerBuilder()
        .WithNamingConvention(UnderscoredNamingConvention.Instance)
        .WithTypeConverter(new TimeSpanToDoubleConverter())
        .Build();

    // --- EncoderSettings Overloads ---

    public static string ToYaml(this EncoderSettings settings) => _serializer.Serialize(settings);

    public static void ToYaml(this EncoderSettings settings, string filePath)
        => File.WriteAllText(filePath, settings.ToYaml());

    public static EncoderSettings FromYaml(this string yamlContent)
        => _deserializer.Deserialize<EncoderSettings>(yamlContent);

    // --- Job Overloads ---

    /// <summary> Converts a Job to a YAML string </summary>
    public static string ToYaml(this Job job) => _serializer.Serialize(job);

    /// <summary> Saves a Job to a YAML file </summary>
    public static void ToYaml(this Job job, string filePath)
        => File.WriteAllText(filePath, job.ToYaml());

    /// <summary> Loads a Job from a YAML string </summary>
    public static Job JobFromYaml(this string yamlContent)
        => _deserializer.Deserialize<Job>(yamlContent);

    // --- Generic File Loader ---

    /// <summary> Generic helper to load any supported type from a file </summary>
    public static T FromYamlFile<T>(string filePath)
    {
        var yaml = File.ReadAllText(filePath);
        return _deserializer.Deserialize<T>(yaml);
    }

    // --- Custom Converter for Full Precision ---

    private class TimeSpanToDoubleConverter : IYamlTypeConverter
    {
        public bool Accepts(Type type) => type == typeof(TimeSpan);

        public object ReadYaml(IParser parser, Type type, ObjectDeserializer nestedObjectDeserializer)
        {
            var scalar = parser.Consume<Scalar>();
            if (double.TryParse(scalar.Value, NumberStyles.Float, CultureInfo.InvariantCulture, out double seconds))
            {
                return TimeSpan.FromSeconds(seconds);
            }
            return TimeSpan.Zero;
        }

        public void WriteYaml(IEmitter emitter, object? value, Type type, ObjectSerializer nestedObjectSerializer)
        {
            var ts = (TimeSpan)value!;
            // "G17" ensures no precision loss for the 100ns ticks
            emitter.Emit(new Scalar(ts.TotalSeconds.ToString("G17", CultureInfo.InvariantCulture)));
        }
    }
}