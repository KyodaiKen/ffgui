#!/bin/bash
PUBLISH_DIR="./publish-win"
UCRT_BIN="/ucrt64/bin"
DOTNET_EXE="/c/Program Files/dotnet/dotnet.exe"

THEME_NAME="dark"
LOCAL_THEME_SOURCE="./theme/$THEME_NAME"

echo "--- 1. Building ---"
rm -rf "$PUBLISH_DIR"
"$DOTNET_EXE" publish -c Release -r win-x64 --self-contained false -p:PublishSingleFile=true

echo "--- 2. Copying DLLs ---"
cp "$UCRT_BIN"/*.dll "$PUBLISH_DIR/" 2>/dev/null

echo "--- 3. Deploying Theme & Icons ---"
# Standard GTK4 Windows Layout
mkdir -p "$PUBLISH_DIR/share/themes/$THEME_NAME/gtk-4.0"
mkdir -p "$PUBLISH_DIR/share/icons"
mkdir -p "$PUBLISH_DIR/etc/gtk-4.0"
mkdir -p "$PUBLISH_DIR/share/glib-2.0/schemas"

# Copy Schemas
cp /ucrt64/share/glib-2.0/schemas/gschemas.compiled "$PUBLISH_DIR/share/glib-2.0/schemas/"

# Copy Theme (Ensure the folder name matches THEME_NAME)
if [ -d "$LOCAL_THEME_SOURCE" ]; then
    echo "Copying theme files..."
    cp -r "$LOCAL_THEME_SOURCE/"* "$PUBLISH_DIR/share/themes/$THEME_NAME/"
fi

# Copy Icons
if [ -d "./gtk-icons" ]; then
    cp -r ./gtk-icons/* "$PUBLISH_DIR/share/icons/"
fi

echo "--- 4. Writing Configs ---"
# settings.ini is the most reliable way to set the theme name
cat <<EOF > "$PUBLISH_DIR/etc/gtk-4.0/settings.ini"
[Settings]
gtk-theme-name=$THEME_NAME
gtk-application-prefer-dark-theme=1
gtk-font-name=Segoe UI 10
EOF

# Use a direct path in gtk.css
echo "@import url(\"../share/themes/$THEME_NAME/gtk-4.0/gtk.css\");" > "$PUBLISH_DIR/etc/gtk-4.0/gtk.css"


echo "--- 5. Create Archive (Using LZMA for maximum SFX compatibility) ---"
# We change lzma2 to lzma to ensure the SFX stub can read it
7z a -sfx/usr/lib/p7zip/7z-win.sfx -t7z -m0=lzma2 -mx=9 -md=256m -mfb=64 -ms=on "$PUBLISH_DIR/ffgui-win-x64-installer.exe" "$PUBLISH_DIR/*"

rm -rf ./bin
rm -rf ./obj
echo "--- DONE ---"
