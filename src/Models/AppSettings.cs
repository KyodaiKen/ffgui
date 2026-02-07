namespace FFGui.Models;

public class AppSettings
{
    public static AppSettings Instance { get; private set; } = new();
    public bool AllowYamlAliases;
    public string FFMpegPath = "";
    
    // Method to update the reference (e.g., after loading from disk)
    public static void Load(AppSettings loadedSettings)
    {
        Instance = loadedSettings;
    }
}