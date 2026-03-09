# FFgui

[![C#](https://img.shields.io/badge/c%23-%23239120.svg?logo=c-sharp&logoColor=white)](https://learn.microsoft.com/en-us/dotnet/csharp/)
[![.NET 10](https://img.shields.io/badge/.NET-10-512bd4.svg?logo=dotnet&logoColor=white)](https://dotnet.microsoft.com/download/dotnet/10.0)
[![GTK](https://img.shields.io/badge/GUI-GTK4-orange.svg)](https://www.gtk.org/)
[![FFmpeg](https://img.shields.io/badge/Engine-FFmpeg-green.svg)](https://ffmpeg.org/)

A powerful, template-driven media converter powered by GTK4 and FFmpeg, written in C# (.NET 10). Designed for high-performance media transcoding with advanced batch job management.

**FFgui** provides a granular interface for controlling individual streams, metadata, and dispositions while maintaining a streamlined workflow through a robust, reusable template system.

## ✨ Features

* **Granular Stream Control:** Modify settings for video, audio, and subtitle streams individually within a single source file.
* **Template-Based Workflow:** Apply global transcoding profiles (e.g., "High Quality H265", "Copy Audio") to streams instantly.
* **Smart Working Directory:** Automatically detects "Portable Mode" (writable application folder) or "Installed Mode" (using XDG data paths on Linux or %APPDATA% on Windows).
* **Dynamic UI Validation:** Real-time checking of template integrity; rows highlight with warnings if referenced templates are missing.
* **Advanced Metadata & Disposition:** Built-in editors for stream-level metadata and FFmpeg disposition flags (default, forced, etc.).
* **Precision Trimming:** Built-in calculation for trim lengths and offsets with a synchronized UI.
* **Batch Processing:** Queue multiple jobs with multi-threaded execution and global progress tracking.

---

## 🚀 Installation & Building

### Prerequisites

* **[.NET 10 SDK](https://dotnet.microsoft.com/download/dotnet/10.0)**
* **GTK4 Libraries:**
    * **Linux:** `libgtk-4-dev` (e.g., `sudo apt install libgtk-4-dev` on Debian/Ubuntu).
    * **Windows:** Make sure GTK4 DLLs are in your PATH or the application folder.
* **FFmpeg:** Must be accessible in your system PATH or configured manually in the application settings.

> **Note:** The first launch performs a full introspection of your FFmpeg capabilities to build a feature cache. This may take 10-30 seconds depending on your hardware and antivirus.

---

### 🐧 Linux Setup

1.  **Clone and Build:**
    ```bash
    git clone [https://github.com/yourusername/ffgui.git](https://github.com/yourusername/ffgui.git)
    cd ffgui
    ./publish-linux.sh
    ```
2.  **Install to System:**
    Navigate to the publish directory and run the included setup script:
    ```bash
    cd bin/Release/net10.0/linux-x64/publish/
    sudo ./setup.sh
    ```
    *The script installs the app to `/opt/ffgui`, registers the icon, and creates a `.desktop` menu entry.*

---

### 🪟 Windows Setup

1.  **Build from Source: (Requires Windows with MSYS2 UCRT environment with gtk fully installed)**
    ```bash
    ./publish-win64.sh
    ```
2.  **Run:**
    * Navigate to `bin\Release\net10.0\win-x64\publish\`.
    * Run `ffgui.exe`.
    * The app runs in **Portable Mode** if the directory is writable, keeping all settings and templates in the local folder.

---

### Installation from Binaries (See Releases)

#### Windows
1. Extract wherever you want, for example c:\Program Files\FFgui (run as administrator in this case)
2. Go to the extraction path
3. Make sure you have the .NET 10 runtime installed. There is a url file in the archive to directly launch the download.
4. Install the runtime.
5. Pin ffgui.exe to wherever you want or create a desktop shortcut
6. Download a FFmpeg Windows Build: https://ffmpeg.org/download.html#build-windows
7. Extract the contents of the bin folder or the folder with the exe and dll files to your installation folder under codecs -> ffmpeg (create the ffmpeg folder)
8. Run FFgui
9. Wait for the introspection to finish
10. Enjoy

#### Linux

1. Make sure you have ffmpeg and dotnet 10 runtime or sdk installed
2. Extract `tar xvf ffgui-linux-x64.tar.xz`
3. Go to the extracted files `cd publish-linux`
4. Run setup `sudo ./setup.sh` to install it in /opt/
5. Delete the install packages
6. Run it from your app menu
7. Wait for the introspection to finish
8. Enjoy!

PS: You can run setup.sh in opt at any time again to uninstall. The reinstall option won't work in that case of course, that only works from a freshly downloaded package. It will basically do the same as uninstall and then error out.

## 🛠 Project Structure

The project has been reorganized into a clean `src/` architecture:

* **`src/Core/`**: The engine room. Contains `FFGuiApp`, `JobRunner`, and FFmpeg introspection logic.
* **`src/Models/`**: Data structures for Jobs, Templates, and FFmpeg capability mapping.
* **`src/UI/`**: GTK4 window definitions and custom widgets (JobSetup, TemplateEditor, etc.).
* **`src/Helpers/`**: Utilities for YAML serialization, shell execution, and path resolution.
* **`templates/`**: Default transcoding profiles included with the application.

---

## 📂 Data Management

FFgui is smart about where it saves your data:

* **Portable Mode:** If the application folder is writable, all `.yaml` settings and templates are stored locally.
* **Installed Mode (Linux):** Settings are stored in `~/.local/share/de.kyo.ffgui/` and system templates are read from `/opt/ffgui/templates/`.
* **Installed Mode (Windows):** Settings are stored in `%APPDATA%\de.kyo.ffgui\`.

---

## 🔮 Future Plans

* **CLI Mode:** Ability to run saved job lists via terminal for automation without the GUI.
* **Enhanced Introspection:** Faster startup by optimizing the FFmpeg capability scan.
* **Theme Support:** Better integration with system-wide Dark/Light mode switching.

## 📜 License

Distributed under the MIT License. See `LICENSE` for more information.
