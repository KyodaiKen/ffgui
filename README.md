# ffGUI

[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![GTK](https://img.shields.io/badge/GUI-GTK4-orange.svg)](https://www.gtk.org/)
[![FFmpeg](https://img.shields.io/badge/Engine-FFmpeg-green.svg)](https://ffmpeg.org/)

A powerful, template-driven GTK4 frontend for FFmpeg, designed for transcoding media files with batch job management.
**ffGUI** provides a granular interface for controlling individual streams, metadata, and dispositions while maintaining a streamlined workflow through a robust template system.

## ✨ Features

* **Granular Stream Control:** Modify settings for video, audio, and subtitle streams individually within a single source file.
* **Template-Based Workflow:** Apply global templates (e.g., "Copy Video", "High Quality H264") to streams instantly to ensure consistency.
* **Dynamic UI Validation:** Real-time checking of template integrity; rows highlight with warnings if referenced templates are missing from the library.
* **Advanced Metadata & Disposition:** Built-in editors for stream-level metadata and FFmpeg disposition flags (default, forced, etc.).
* **Precision Trimming:** Automatic calculation of trim lengths, starts, and ends with a synchronized UI.
* **Batch Processing:** Drag-and-drop multiple files to create a job queue with global progress tracking and multi-threaded execution.
* **Job Cloning & Editing:** Clone existing jobs to tweak settings without starting from scratch.

## 🚀 Installation

### Prerequisites

* **Python 3.10+**
* **GTK4** & **PyGObject**
* **FFmpeg** (installed and accessible in your PATH OR set up the location in the settings)

NOTICE: The first start may take a while as the application does an introspection of the FFMPEG capabilities.
In a later version, this will run a lot faster.

### 🐧 Linux / 🍎 MacOS Setup

1. Clone the repository:
    ```bash
    git clone [https://github.com/yourusername/ffgui.git](https://github.com/yourusername/ffgui.git)
    cd ffgui
    ```
2. Install dependencies:
    ```bash
     pip install PyGObject pycountry pyyaml
    ```
    NOTICE: PyGObject is build from sources, so make sure to read the PyGObject documentation.
3. Run the application:
    ```bash
    python ffgui.py
    ```
    
### 🪟 Windows 64-Bit only
A Windows UCRT 64-Bit binary can be found under releases.

1. Extract the 7z file wherever you like
2. Place your favorite FFMPEG under `codecs\ffmpeg`.
3. Run `ffgui.exe`

OR

1. Extract the 7z file wherever you like
2. Run `ffgui.exe`
3. Go to the burger menu and then Settings
4. Point to your FFMPEG binary directory and click "Save & Rescan"

NOTICE: Under Windows it can take a while until the application first starts due to the Smart Screen Filter and introspection can be slow depending on the antivirus solution you are using.

## 🛠 Project Structure

* `Core/`: The engine room, containing the `JobRunner` and utility functions for time and media parsing.
* `Models/`: Data logic for jobs (`JobsDataModel`) and templates (`TemplateDataModel`).
* `UI/:` GTK4 window definitions:
    * `JobSetupWindow`: The primary interface for configuring file sources.
    * `SourceStreamRow`: Individual widget logic for stream settings.
    * `TemplateEditorWindow`: Create and modify reusable transcoding profiles.
    * and more...
    
## 📂 Data Management

* The application stores templates and job configurations in YAML format in `templates/`
* Job list are also stored in the YAML format for easy text based editing

## 🔮 Future plans

* Polish and improvements.
* Adding a command line mode to run saved job lists via command line for those who want to automate FFMPEG using ffgui without using the GUI.

## 🤝 Contributing

1. Fork the Project
2. Create your Feature Branch (git checkout -b feature/AmazingFeature)
3. Commit your Changes (git commit -m 'Add some AmazingFeature')
4. Push to the Branch (git push origin feature/AmazingFeature)
5. Open a Pull Request

## 📜 License

Distributed under the MIT License. See `LICENSE` for more information.
