namespace FFGui.Models;

using YamlDotNet.Core;
using YamlDotNet.Core.Events;
using YamlDotNet.Serialization;
using YamlDotNet.Serialization.NamingConventions;
using System.Globalization;
using System.IO;

public static class YamlExtensions
{
    // Serializer with Aliases DISABLED (Human Readable)
    private static readonly ISerializer _serializerPlain = CreateBuilder(disableAliases: true).Build();

    // Serializer with Aliases ENABLED (Compressed/Default YAML behavior)
    private static readonly ISerializer _serializerAliased = CreateBuilder(disableAliases: false).Build();

    private static readonly IDeserializer _deserializer = new DeserializerBuilder()
        .WithNamingConvention(PascalCaseNamingConvention.Instance)
        // Map the YAML tag to the C# type
        .WithTagMapping("!TranscodingTemplate", typeof(TranscodingTemplate))
        .WithTagMapping("!FilterTemplate", typeof(FilterTemplate))
        .WithTagMapping("!ContainerSettingsTemplate", typeof(ContainerTemplate))
        .WithAttemptingUnquotedStringTypeDeserialization()
        .IgnoreUnmatchedProperties()
        .Build();

    // Helper to keep logic DRY
    private static SerializerBuilder CreateBuilder(bool disableAliases)
    {
        var builder = new SerializerBuilder()
            .WithNamingConvention(PascalCaseNamingConvention.Instance)
            .WithQuotingNecessaryStrings()
            .ConfigureDefaultValuesHandling(DefaultValuesHandling.OmitNull)
            // This tells the serializer: "When you see this type, write this !tag"
            .WithTagMapping("!TranscodingTemplate", typeof(TranscodingTemplate))
            .WithTagMapping("!FilterTemplate", typeof(FilterTemplate))
            .WithTagMapping("!ContainerSettingsTemplate", typeof(ContainerTemplate))
            .WithIndentedSequences();
        if (disableAliases)
            builder.DisableAliases();

        return builder;
    }

    /// <summary> 
    /// Dynamically selects the serializer based on AppSettings
    /// </summary>
    private static ISerializer GetActiveSerializer()
    {
        // Replace 'App.Settings' with your actual static reference
        return AppSettings.Instance.AllowYamlAliases ? _serializerAliased : _serializerPlain;
    }

    // --- Generic Extensions ---

    /// <summary> Converts any object to a YAML string </summary>
    public static string ToYaml<T>(this T obj) where T : notnull
        => GetActiveSerializer().Serialize(obj);

    /// <summary> Saves any object to a YAML file </summary>
    public static void ToYaml<T>(this T obj, string filePath) where T : notnull
        => File.WriteAllText(filePath, obj.ToYaml());

    /// <summary> Deserializes a YAML string into a specific type </summary>
    public static T FromYaml<T>(this string yamlContent)
        => _deserializer.Deserialize<T>(yamlContent);

    /// <summary> Loads and deserializes a YAML file into a specific type </summary>
    public static T FromYamlFile<T>(string filePath)
    {
        if (!File.Exists(filePath))
            throw new FileNotFoundException($"YAML file not found: {filePath}");

        return File.ReadAllText(filePath).FromYaml<T>();
    }
}