namespace FFGui.Core;

using Gtk;
using Gio;
using Gdk;
using System;
using System.IO;
using File = System.IO.File;
// Alias the Task to avoid the Gio/System conflict
using Task = System.Threading.Tasks.Task;
using FFGui.Models;
using FFGui.Services;
using FFGui.UI;

#if WINDOWS
#pragma warning disable CA1416
using Microsoft.Win32;
#pragma warning restore CA1416
#endif

public class FFGuiApp : Gtk.Application

{
    private JobListWindow? _mainWindow;
    public AppSettings Settings;
    public string WorkingDir;
    public string SettingsFileName;
    public string FFMpegPath = null!;
    public string FFProbePath = null!;
    public string FFPlayPath = null!;
    public string FFMpegCachePath;
    public string[] TemplatePaths;
    public bool PortableMode = false;

    // --- Application state ---
    public FFmpegCache Cache { get; private set; }
    public Dictionary<int, Job> Jobs;

    public Dictionary<string, string> Languages;

    public FFGuiApp() : base()
    {
        // Set properties manually to avoid the 'blittable' structure error
        ApplicationId = "de.kyo.ffgui";
        Flags = Gio.ApplicationFlags.FlagsNone;

        Jobs = [];

        Cache = new();

        // Check if the assembly directory is writable. If not, we use the user's home directory as the base directory.
        string assemblyDir = AppDomain.CurrentDomain.BaseDirectory;
        bool isWritable = false;
        try
        {
            string testPath = Path.Combine(assemblyDir, Path.GetRandomFileName());
            using (FileStream fs = File.Create(testPath, 1, FileOptions.DeleteOnClose)) { }
            isWritable = true;
        }
        catch
        {
            isWritable = false;
        }

        if (isWritable)
        {
            WorkingDir = assemblyDir;
            PortableMode = true;
#if VERBOSE
            Console.WriteLine
            (
                $"""
                {ApplicationId}: INFO - Running in portable mode since assy directory is writable.
                {ApplicationId}: WorkingDir = '{WorkingDir}'
                """
            );
#endif
        }
        else
        {
            // Fallback to OS-specific User Home
            if (OperatingSystem.IsWindows())
            {
                // %APPDATA%
                string appData = Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData);
                WorkingDir = Path.Combine(appData, ApplicationId);
            }
            else
            {
                // Linux/macOS: ~/.local/share/de.kyo.ffgui
                string home = Environment.GetFolderPath(Environment.SpecialFolder.UserProfile);
                WorkingDir = Path.Combine(home, ".local", "share", ApplicationId);
            }

            // Create working directory if it doesn't already exist
            if (!System.IO.Directory.Exists(WorkingDir)) System.IO.Directory.CreateDirectory(WorkingDir);
#if VERBOSE
            Console.WriteLine
            (
                $"""
                {ApplicationId}: INFO - Running in installed mode since assy directory is NOT writable.
                {ApplicationId}: WorkingDir = '{WorkingDir}'
                """
            );
#endif
        }

        // Initialize cache directory
        string cacheDir = Path.Combine(WorkingDir, ".cache");
        if (!System.IO.Directory.Exists(cacheDir)) System.IO.Directory.CreateDirectory(cacheDir);
        FFMpegCachePath = Path.Combine(cacheDir, "ffmpeg.mpac");
#if VERBOSE
        Console.WriteLine($"{ApplicationId}: FFMpegCachePath = '{FFMpegCachePath}'");
#endif

        // Initialize template directories
        var systemTemplateDirectory = Path.Combine(assemblyDir, "templates");
        if (!System.IO.Directory.Exists(systemTemplateDirectory))
            System.IO.Directory.CreateDirectory(systemTemplateDirectory);
        
        var userTemplateDirectory = Path.Combine(WorkingDir, "templates");
        if (WorkingDir == assemblyDir)
        {
#if VERBOSE
            Console.WriteLine($"{ApplicationId}: INFO - Portable mode: user template directory will not be used.");
#endif
            userTemplateDirectory = String.Empty;
        }
        else
        {
            if (!System.IO.Directory.Exists(userTemplateDirectory))
                System.IO.Directory.CreateDirectory(userTemplateDirectory);
        }

        if (String.Empty.Equals(userTemplateDirectory))
            TemplatePaths = [systemTemplateDirectory];
        else
            TemplatePaths = [systemTemplateDirectory, userTemplateDirectory];

#if VERBOSE
        Console.WriteLine
        (
            $"""
            {ApplicationId}: System Template Directory = '{systemTemplateDirectory}'
            {ApplicationId}: User Template Directory  =  '{userTemplateDirectory}'
            """
        );
#endif

        // Load settings
        SettingsFileName = Path.Combine(WorkingDir, "settings.yaml");
        try
        {
            Settings = YamlExtensions.FromYamlFile<AppSettings>(SettingsFileName);
#if VERBOSE
            Console.WriteLine($"{ApplicationId}: Loaded settings from '{SettingsFileName}'");
#endif
        }
        catch
        {
            // Settings file not found, using defaults and then saving the settings file.
            Settings = new()
            {
                FFMpegPath = String.Empty
            };
#if VERBOSE
            Console.WriteLine($"{ApplicationId}: Settings file '{SettingsFileName}' does not exist, created it with defaults.");
#endif
            Settings.ToYaml(SettingsFileName);
        }

        //Update static state
        AppSettings.Load(Settings);

        ResolveFFmpegBinaries();

        this.OnActivate += OnAppActivate;

        // Load language list
        Helpers.LanguageHelper.Initialize();
        Languages = Helpers.LanguageHelper.GetAll();
    }
    
    public void ResolveFFmpegBinaries()
    {
        // Resolve FFMPEG binaries
        FFMpegPath = HelperFunctions.ResolveBinary("ffmpeg", Settings.FFMpegPath) ?? string.Empty;
        FFProbePath = HelperFunctions.ResolveBinary("ffprobe", Settings.FFMpegPath) ?? string.Empty;
        FFPlayPath = HelperFunctions.ResolveBinary("ffplay", Settings.FFMpegPath) ?? string.Empty;
#if VERBOSE
        Console.WriteLine
        (
            $"""
            {ApplicationId}: FFMpegPath = '{FFMpegPath}'
            {ApplicationId}: FFProbePath = '{FFProbePath}'
            {ApplicationId}: FFPlayPath = '{FFPlayPath}'
            """
        );
#endif
        
        if (!File.Exists(FFMpegPath))
        {
            Console.WriteLine($"{ApplicationId}: FATAL ERROR - 'ffmpeg' not found in path above! Quitting...");
            Quit();
        }
        if (!File.Exists(FFProbePath))
        {
            Console.WriteLine($"{ApplicationId}: FATAL ERROR - 'ffprobe' not found in path above! Quitting...");
            Quit();
        }
        if (!File.Exists(FFPlayPath))
        {
            Console.WriteLine($"{ApplicationId}: FATAL ERROR - 'ffplay' not found in path above! Quitting...");
            Quit();
        }
    }

    public async Task ReinitAsync(bool force = false)
    {
        // We do NOT show the progress window yet
        var progressWin = new IntrospectionWindow();
        this.AddWindow(progressWin);

        // Handle the "Abort & Quit" logic from the window side
        progressWin.OnCloseRequest += (s, args) =>
        {
            this.Quit();
            return true;
        };

        try
        {
            bool needsIntrospection = true;
            string currentHeader = await Task.Run(() => RunSimpleCmd(FFMpegPath, "-version"));

            if (!force)
            {
                if (System.IO.File.Exists(FFMpegCachePath))
                {
                    try
                    {
                        var existingCache = FFmpegCache.LoadFromFile(FFMpegCachePath);
                        if (existingCache.FFmpegVersionHeader == currentHeader && existingCache.CacheVersion == 1)
                        {
                            this.Cache = existingCache;
                            needsIntrospection = false;
                        }
                    }
                    catch { /* Corrupt cache */ }
                }
            }

            GLib.Functions.IdleAdd(0, () =>
            {
                if (!needsIntrospection)
                {
                    progressWin.Destroy(); // Clean up the hidden window
                    LaunchMainWindow();
                }
                else
                {
                    progressWin.Show(); // Now show it only because we need it
                    _ = RunIntrospection(progressWin, currentHeader);
                }
                return false;
            });
        }
        catch (Exception ex)
        {
            Console.WriteLine($"Startup Error: {ex.Message}");
            GLib.Functions.IdleAdd(0, () => { this.Quit(); return false; });
        }
    }
    private void OnAppActivate(GObject.Object sender, EventArgs e)
    {
        SetupTheme(Gdk.Display.GetDefault());
        _ = ReinitAsync();
    }

    private async System.Threading.Tasks.Task RunIntrospection(IntrospectionWindow win, string header)
    {
        try
        {
            // Initialize the root Cache object
            var newCache = new FFmpegCache
            {
                FFmpegVersionHeader = header,
                CacheVersion = 1,
                Codecs = new(),
                Formats = new(),
                Filters = new(),
                PixelFormats = new(),
                Globals = new() 
            };

            // Parse Globals using your renamed FFmpegGlobalsParser
            UpdateUI(win, "Analyzing Globals...", 0.05);
            var globalParser = new FFmpegGlobalsParser(FFMpegPath);
            // This now returns the struct directly as we designed in Step 2
            newCache.Globals = await globalParser.ParseGlobalsAsync();

            // Parse Pixel Formats
            UpdateUI(win, "Analyzing Pixels...", 0.01);
            newCache.PixelFormats = await new FFmpegPixelFormatParser(FFMpegPath).ParseAllAsync();

            // Parse Filters (with progress callback)
            newCache.Filters = await new FFmpegFilterParser(FFMpegPath).ParseAllAsync((name, p) =>
                UpdateUI(win, $"Filter: {name}", 0.01 + (p * 0.33)));

            // Parse Formats (with progress callback)
            newCache.Formats = await new FFmpegFormatParser(FFMpegPath).ParseAllAsync((name, p) =>
                UpdateUI(win, $"Format: {name}", 0.34 + (p * 0.33)));

            // Parse Codecs (the heavy lifting)
            newCache.Codecs = await new FFmpegCodecParser(FFMpegPath).ParseAllAsync((name, p) =>
                UpdateUI(win, $"Codec: {name}", 0.67 + (p * 0.33)));

            // Finalize and Save to .cache
            await newCache.SaveToFileAsync(FFMpegCachePath);
            this.Cache = newCache;

            // UI Update: Close introspection and launch main app
            GLib.Functions.IdleAdd(0, () =>
            {
                win.Destroy();
                LaunchMainWindow();
                return false;
            });
        }
        catch (Exception ex)
        {
            Console.WriteLine($"Introspection failed: {ex}");
            // In case of failure, you might want to show a Gtk.MessageDialog 
            // before calling this.Quit()
        }

        await Task.CompletedTask;
    }

    private void LaunchMainWindow()
    {
        //TESTING
        // #if DEBUG
        // if (Cache.Globals.Video.TryGetValue("aspect", out var obj))
        //   Console.WriteLine(obj.ToYaml());
        // #endif

        if (_mainWindow != null)
        {
            _mainWindow.Present();
            return;
        }

        _mainWindow = new JobListWindow(this);

        // Clean up the reference if the user closes the window
        _mainWindow.OnCloseRequest += (s, args) =>
        {
            _mainWindow = null;
            return false; // Let the window actually close
        };

        _mainWindow.Show();
    }

    private void UpdateUI(IntrospectionWindow win, string text, double progress)
    {
        GLib.Functions.IdleAdd(0, () =>
        {
            win.UpdateProgress(text, progress);
            return false;
        });
    }

    private async Task<string> RunSimpleCmd(string path, string args)
    {
        var psi = new System.Diagnostics.ProcessStartInfo(path, args)
        {
            RedirectStandardOutput = true,
            UseShellExecute = false,
            CreateNoWindow = true
        };
        using var proc = System.Diagnostics.Process.Start(psi);
        return await proc!.StandardOutput.ReadToEndAsync();
    }

    void SetupTheme(Display? display)
    {
        if (display == null) return;

        var iconTheme = Gtk.IconTheme.GetForDisplay(display);
        iconTheme.AddSearchPath(AppDomain.CurrentDomain.BaseDirectory);

        // Optional: Keep your custom icons subfolder if you use it for other icons
        string iconDir = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "gtk-icons");
        if (Directory.Exists(iconDir)) iconTheme.AddSearchPath(iconDir);

#if WINDOWS
#pragma warning disable CA1416
    bool useDark = true;
    try
        {
            // Check Windows Registry for Light/Dark mode
            using (RegistryKey? key = Registry.CurrentUser.OpenSubKey(@"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"))
            {
                if (key != null)
                {
                    // 1 = Light Mode, 0 = Dark Mode
                    object? registryValue = key.GetValue("AppsUseLightTheme");
                    if (registryValue is int i && i == 1)
                        useDark = false;
                }
            }
        }
        catch (Exception ex)
        {
            Console.WriteLine($"Registry check failed, defaulting to dark: {ex.Message}");
        }


        // --- Apply the Theme Preference ---
        var settings = Gtk.Settings.GetForDisplay(display);
        if (settings != null)
        {
            // This is the magic line for Adwaita
            settings.GtkApplicationPreferDarkTheme = useDark;
            settings.GtkFontName = "Segoe UI 10";
        }
#pragma warning restore CA1416
#endif
        // string subfolder = "dark";

        // try
        // {

        //     // Check Windows Registry for Light/Dark mode
        //     using (RegistryKey? key = Registry.CurrentUser.OpenSubKey(@"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"))
        //     {
        //         if (key != null)
        //         {
        //             object? registryValue = key.GetValue("AppsUseLightTheme");
        //             if (registryValue is int i && i == 1)
        //             {
        //                 subfolder = "light";
        //             }
        //         }
        //     }
        // }
        // catch (Exception ex)
        // {
        //     Console.WriteLine($"Registry check failed, defaulting to dark: {ex.Message}");
        // }

        // string iconDirGtk = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "gtk-icons");
        // if (Directory.Exists(iconDirGtk)) iconTheme.AddSearchPath(iconDirGtk);

        //         var themeProvider = Gtk.CssProvider.New();
        //         string themePath = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "share", "themes", subfolder, "gtk-4.0", "gtk.css");

        //         if (System.IO.File.Exists(themePath))
        //         {
        //             themeProvider.LoadFromPath(themePath);

        //             // Use Priority 800 (User) to make sure it overrides Adwaita
        //             Gtk.StyleContext.AddProviderForDisplay(
        //                 display,
        //                 themeProvider,
        //                 Gtk.Constants.STYLE_PROVIDER_PRIORITY_USER
        //             );
        // #if VERBOSE
        //             Console.WriteLine($"Successfully loaded {subfolder} theme from: {themePath}");
        // #endif
        //          }

        //         var settings = Gtk.Settings.GetForDisplay(display);
        //         if (settings != null)
        //         {
        //             settings.GtkFontName = "Segoe UI 10";
        //         }
        // #pragma warning restore CA1416
        // #endif

        // Load custom CSS (similar to your Python style)
        var provider = Gtk.CssProvider.New();
        string css = @"
            /* JobSetupWindow */
            /* Target the rows inside the streams list specifically */
            #streams_list row:hover {
                background-color: transparent;
            }
            /* Optional: Make sure they don't look 'selected' either since mode is NONE */
            #streams_list row:selected {
                background-color: transparent;
            }
                                    
            .container-tag {
                background-color: alpha(@theme_fg_color, 0.05);
                border: 1px solid mix(@theme_fg_color, @theme_bg_color, 0.8);
                border-radius: 6px;
                padding: 2px;
            }
            .container-tag label {
                margin: 0 6px 0 0;
                font-weight: bold;
                line-height: 100%;
            }

            .fb-dispositions {
                background-color: alpha(@theme_bg_color, 1);
                padding: 2px;
            }

            .disposition-tag {
                background-color: alpha(@theme_fg_color, 0.05);
                border: 1px solid mix(@theme_fg_color, @theme_bg_color, 0.8);
                border-radius: 6px;
                padding: 2px 2px 2px 8px;
            }
            .disposition-tag label {
                margin: 0 4px 0 0;
                font-weight: bold;
                line-height: 100%;
            }

            flowboxchild {
                padding: 0;
                margin: 0;
            }

            .success-icon {
                color: #2ec27e;
            }
            .error-icon {
                color: #e01b24;
            }

            #ffmpeg_error_log {
                font-family: 'JetBrains Mono NL', monospace;
                font-size: 10pt;
            }

            .job-lbl-info, .job-lbl-status-info { font-size: 85%; font-family: 'JetBrainsMono NL', monospace; }

            /* TemplateEditorWindow */
            .codec-tag { background-color: alpha(@theme_fg_color, 0.05); border: 1px solid mix(@theme_fg_color, @theme_bg_color, 0.8); border-radius: 6px; padding: 2px; }
            .codec-tag label { margin-left: 6px; margin-right: 6px; font-weight: bold; }
            dropdown > button > box > stack > row.activatable { background-color: transparent; }
            #template-editor-column popover box { min-width: 180px; }
            .warning-badge {
                color: @warning_color;
                border-radius: 4px;
                padding: 2px 8px;
                font-size: 0.9em;
                font-weight: bold;
            }

            .introspection-label { font-size: 14px; font-weight: bold; }
            progressbar text { opacity: 1.0; font-size: 12px; color: @theme_fg_color; font-family: 'JetBrainsMono NL', monospace; }

            list row:selected,
            listview row:selected {
                /* Mixes theme accent color with 60% transparency */
                background-color: color-mix(in srgb, @theme_selected_bg_color, transparent 60%);
                
                /* Overrides the text color to stay readable (usually black or white) */
                color: inherit;
                
                /* Removes the high-contrast focus ring that often clashes with soft colors */
                outline-style: none;
            }

            list row:hover,
            listview row:hover {
                /* Mixes theme accent color with 50% transparency */
                background-color: color-mix(in srgb, @theme_selected_bg_color, transparent 50%);
                
                /* Overrides the text color to stay readable (usually black or white) */
                color: inherit;
                
                /* Removes the high-contrast focus ring that often clashes with soft colors */
                outline-style: none;
            }

            list row:active,
            listview row:active {
                background-color: @theme_selected_bg_color;
                
                /* Overrides the text color to stay readable (usually black or white) */
                color: inherit;
                
                /* Removes the high-contrast focus ring that often clashes with soft colors */
                outline-style: none;
            }

            /* Optional: Make it even softer when the window isn't active */
            list row:selected:backdrop,
            listview row:selected:backdrop {
                background-color: color-mix(in srgb, @theme_selected_bg_color, transparent 90%);
            }
        ";

        provider.LoadFromData(css, css.Length);
        Gtk.StyleContext.AddProviderForDisplay(display, provider, 900);

// #if WINDOWS
// #pragma warning disable CA1416
//         css = @"
//             /* Reset the Adwaita circular backgrounds */
//             windowcontrols button {
//                 border-radius: 0;
//                 background-color: transparent;
//                 background-image: none;
//                 box-shadow: none;
//                 padding: 0;
//                 margin: 0;
//                 min-width: 42px; /* Breeze standard width */
//                 min-height: 24px;
//             }

//             /* Allow Breeze icons to show through */
//             windowcontrols button image {
//                 background: none;
//                 box-shadow: none;
//                 -gtk-icon-shadow: none;
//                 opacity: 1;
//             }
//         ";

//         provider.LoadFromData(css, css.Length);
//         Gtk.StyleContext.AddProviderForDisplay(display, provider, 600);
// #pragma warning restore CA1416
// #endif
    }
}