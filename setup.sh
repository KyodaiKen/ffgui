#!/bin/bash

# Configuration
APP_NAME="FFGui"
APP_ID="de.kyo.ffgui"
BINARY_NAME="ffgui"
INSTALL_DIR="/opt/$BINARY_NAME"
DESKTOP_FILE="/usr/share/applications/$APP_ID.desktop"
ICON_DIR="/usr/share/icons/hicolor/scalable/apps"
ICON_NAME="$APP_ID.svg"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

function msg() { echo -e "${GREEN}[*] $1${NC}"; }
function err() { echo -e "${RED}[!] $1${NC}"; }

# Making sure script is run with sudo
if [ "$EUID" -ne 0 ]; then
  err "Please run as root (use sudo)."
  exit 1
fi

# --- .NET Detection Logic ---

check_dotnet() {
    msg "Checking for .NET 10 runtime..."
    
    # Check if dotnet is in PATH and version starts with 10
    if command -v dotnet >/dev/null 2>&1; then
        local version=$(dotnet --version 2>/dev/null)
        if [[ "$version" == 10.* ]]; then
            msg ".NET $version found."
            return 0
        fi
    fi

    err ".NET 10 runtime not found."
    read -p "Would you like to attempt to install the .NET 10 runtime now? (y/N) " confirm
    if [[ $confirm != [yY] ]]; then
        err "Installation aborted. .NET 10 runtime is required to run FFGui."
        exit 1
    fi

    install_dotnet_dependencies
}

install_dotnet_dependencies() {
    # Identify Package Manager
    if command -v apt-get >/dev/null 2>&1; then
        # Ubuntu, Linux Mint, Debian
        msg "Detected APT-based system. Installing dotnet-runtime-10.0..."
        apt-get update
        apt-get install -y dotnet-runtime-10.0

    elif command -v dnf >/dev/null 2>&1; then
        # Fedora, Bazzite (Bazzite uses rpm-ostree, but dnf works in the container/layer)
        msg "Detected DNF-based system. Installing dotnet-runtime-10.0..."
        dnf install -y dotnet-runtime-10.0

    elif command -v pacman >/dev/null 2>&1; then
        # CachyOS, SteamDeck OS (Arch-based)
        msg "Detected Arch-based system (CachyOS/SteamDeck)."
        
        # SteamDeck OS specific: Check if filesystem is locked
        if command -v steamos-readonly >/dev/null 2>&1; then
            err "SteamDeck detected. Ensure you have run 'steamos-readonly disable' if this fails."
        fi
        
        # Note: In Arch, .NET is often in the Community repo or AUR
        # The official Arch package name is 'dotnet-runtime' (versioned by the repo state)
        # To specifically target 10 before it hits 'latest', use:
        pacman -Sy --noconfirm dotnet-runtime-10.0 || pacman -Sy --noconfirm dotnet-runtime
        
    else
        err "Could not determine package manager. Please install .NET 10 manually."
        exit 1
    fi
}

uninstall_app() {
    msg "Uninstalling $APP_NAME..."

    rm -rf "$INSTALL_DIR"
    rm -f "$DESKTOP_FILE"
    rm -f "$ICON_DIR/$ICON_NAME"

    # Refresh system caches
    update-desktop-database /usr/share/applications
    gtk-update-icon-cache /usr/share/icons/hicolor

    msg "Uninstallation complete. (User config files in home directory were not touched)."
}

install_app() {
    msg "Installing $APP_NAME to $INSTALL_DIR..."
    check_dotnet

    # 1. Create directory structure
    mkdir -p "$INSTALL_DIR"
    mkdir -p "$ICON_DIR"

    # 2. Copy files
    cp -rf ./* "$INSTALL_DIR/"

    # 3. Set permissions on the application binary
    chmod +x "$INSTALL_DIR/$BINARY_NAME"

    # 4. Handle Icon

    rm -f "$ICON_DIR/$ICON_NAME"

    cat <<EOF > "$ICON_DIR/$ICON_NAME"
<?xml version="1.0" encoding="UTF-8"?>
<svg width="128" height="128" version="1.1" viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">
 <defs>
  <linearGradient id="linearGradient11" x1="9.6716" x2="51.187" y1="5.0923" y2="51.472" gradientTransform="matrix(-.91417 0 0 -.91429 59.425 59.43)" gradientUnits="userSpaceOnUse">
   <stop stop-color="#00ff7b" offset="0"/>
   <stop stop-color="#ac00ff" offset="1"/>
  </linearGradient>
 </defs>
 <path d="m59.425 63.544a4.1138 4.1143 0 0 0 4.1138-4.1143 4.1138 4.1143 0 0 0-4.1138-4.1143h-8.3525l11.261-11.263a4.1142 4.1147 0 0 0 1.2052-2.9089v-18.286a4.1142 4.1147 0 0 0-7.0224-2.9089l-35.362 35.366h-6.6492l47.828-47.834a4.1142 4.1147 0 0 0-2.9086-7.0232h-18.283a4.1142 4.1147 0 0 0-2.9086 1.2054l-29.545 29.548v-6.65l17.078-17.08a4.1142 4.1147 0 0 0-2.9086-7.0232h-18.283a4.1138 4.1143 0 0 0-4.1138 4.1143 4.1138 4.1143 0 0 0 4.1138 4.1143h8.3525l-11.261 11.263a4.1142 4.1147 0 0 0-1.2052 2.9089v18.286a4.1142 4.1147 0 0 0 7.0224 2.9089l35.362-35.366h6.6492l-47.828 47.834a4.1142 4.1147 0 0 0 2.9086 7.0232h18.283a4.1142 4.1147 0 0 0 2.9086-1.2054l29.545-29.548v6.65l-17.078 17.08a4.1142 4.1147 0 0 0 2.9086 7.0232z" fill="url(#linearGradient11)" stop-color="#000000" stroke="#00d023" stroke-linecap="round" stroke-linejoin="round" stroke-width=".91408"/>
 <path d="m3.8139 63.217h-3.3487v-20.501h8.2722v3.9623h-4.9234v4.6514h4.5646v3.9623h-4.5646zm10.844 0h-3.3487v-20.501h8.2722v3.9623h-4.9234v4.6514h4.5646v3.9623h-4.5646zm13.036-11.743h5.8802v10.825q-1.1162 0.54553-2.4318 0.89008-1.2956 0.31584-2.8305 0.31584-3.1494 0-4.9434-2.6415-1.794-2.6702-1.794-7.9246 0-3.2158 0.85712-5.5702 0.85712-2.3831 2.5115-3.6465 1.6744-1.2921 4.0863-1.2921 1.2159 0 2.3521 0.37326 1.1561 0.34455 2.0332 0.89008l-1.0963 3.8762q-0.69765-0.48811-1.5348-0.77523-0.83718-0.31584-1.7541-0.31584-1.2956 0-2.1926 0.86137-0.87705 0.83266-1.3156 2.3257-0.43852 1.4643-0.43852 3.3593 0 2.9574 0.83718 4.7088 0.85712 1.7227 2.6511 1.7227 0.49832 0 0.95678-0.08613t0.79732-0.17227v-3.79h-2.6311zm20.85 4.0772q0 2.3544-0.67772 4.1346-0.65779 1.7802-1.9933 2.8138-1.3156 1.0049-3.3487 1.0049-2.8703 0-4.3852-2.1247t-1.5149-5.7999v-12.863h3.4085v12.318q0 2.3544 0.63786 3.3593 0.65779 1.0049 1.9335 1.0049 1.3355 0 1.9335-1.0336 0.61792-1.0624 0.61792-3.3593v-12.289h3.3886zm9.1492 7.6662h-6.9167v-2.7851l1.7541-1.0624v-12.806l-1.7541-1.0624v-2.7851h6.9167v2.7851l-1.7541 1.0624v12.806l1.7541 1.0624z" fill="#2c004e" stroke="#a0f" stroke-width=".93047" aria-label="FFGUI"/>
</svg>
EOF

    if [ -f "$INSTALL_DIR/$ICON_NAME" ]; then
        cp -f "$INSTALL_DIR/$ICON_NAME" "$ICON_DIR/"
        # Making sure the icon is readable by all users
        chmod 644 "$ICON_DIR/$ICON_NAME"
    fi

    # 5. Generate Desktop Entry
    msg "Generating desktop entry..."

    rm -f "$DESKTOP_FILE"

    cat <<EOF > "$DESKTOP_FILE"
[Desktop Entry]
Type=Application
Name=$APP_NAME
GenericName=Video Converter
Comment=FFmpeg Graphical User Interface
Exec=$INSTALL_DIR/$BINARY_NAME
Path=$INSTALL_DIR
Icon=$APP_ID
Terminal=false
Categories=AudioVideo;Video;
StartupWMClass=$APP_ID
EOF

    # 6. CRITICAL: Set executable bit on the desktop file itself
    chmod +x "$DESKTOP_FILE"

    # 7. Refresh system caches
    update-desktop-database /usr/share/applications
    gtk-update-icon-cache -f -t /usr/share/icons/hicolor

    # Force KDE to see the change
    if command -v kbuildsycoca6 &> /dev/null; then
        kbuildsycoca6 --noincremental
    elif command -v kbuildsycoca5 &> /dev/null; then
        kbuildsycoca5 --noincremental
    fi

    msg "Installation successful! The app should now appear in your menu."
}

# --- Main Logic ---

if [ -d "$INSTALL_DIR" ]; then
    echo -e "${RED}$APP_NAME is already installed.${NC}"
    read -p "Would you like to (u)ninstall, (r)einstall, or (c)ancel? [u/r/c]: " choice
    case "$choice" in
        u|U ) uninstall_app; exit 0 ;;
        r|R ) uninstall_app; install_app; exit 0 ;;
        * ) msg "Operation cancelled."; exit 0 ;;
    esac
else
    install_app
fi
