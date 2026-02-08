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
    * **Windows:** Ensure GTK4 DLLs are in your PATH or the application folder.
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
