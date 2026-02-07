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

    # 1. Create directory structure
    mkdir -p "$INSTALL_DIR"
    mkdir -p "$ICON_DIR"

    # 2. Copy files
    cp -rf ./* "$INSTALL_DIR/"

    # 3. Set permissions on the application binary
    chmod +x "$INSTALL_DIR/$BINARY_NAME"

    # 4. Handle Icon
    if [ -f "$INSTALL_DIR/$ICON_NAME" ]; then
        cp -f "$INSTALL_DIR/$ICON_NAME" "$ICON_DIR/"
        # Ensure the icon is readable by all users
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
