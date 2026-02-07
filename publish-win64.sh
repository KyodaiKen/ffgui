#!/bin/bash
PUBLISH_DIR="./publish-win"
UCRT_BIN="/ucrt64/bin"
DOTNET_EXE="/c/Program Files/dotnet/dotnet.exe"

THEME_NAME="dark"
LOCAL_THEME_SOURCE="./theme/$THEME_NAME"

echo "--- 1. Building ---"
rm -rf "$PUBLISH_DIR"
"$DOTNET_EXE" publish -c Release -r win-x64 -p:SelfContained=false -p:PublishSingleFile=true

echo "--- 2. Copying DLLs ---"
#cp "$UCRT_BIN"/*.dll "$PUBLISH_DIR/" 2>/dev/null

DLL_LIST="libLerc.dll libbrotlicommon.dll libbrotlidec.dll libbz2-1.dll libcairo-2.dll libcairo-gobject-2.dll libcairo-script-interpreter-2.dll libdatrie-1.dll libdeflate.dll libepoxy-0.dll libexpat-1.dll libffi-8.dll libfontconfig-1.dll libfreetype-6.dll libfribidi-0.dll libgcc_s_seh-1.dll libgdk_pixbuf-2.0-0.dll libgio-2.0-0.dll libglib-2.0-0.dll libgmodule-2.0-0.dll libgobject-2.0-0.dll libgraphene-1.0-0.dll libgraphite2.dll libgstallocators-1.0-0.dll libgstaudio-1.0-0.dll libgstbase-1.0-0.dll libgstd3d12-1.0-0.dll libgstd3dshader-1.0-0.dll libgstgl-1.0-0.dll libgstpbutils-1.0-0.dll libgstplay-1.0-0.dll libgstreamer-1.0-0.dll libgsttag-1.0-0.dll libgstvideo-1.0-0.dll libgtk-4-1.dll libharfbuzz-0.dll libharfbuzz-gobject-0.dll libharfbuzz-subset-0.dll libiconv-2.dll libintl-8.dll libjbig-0.dll libjpeg-8.dll liblzma-5.dll liblzo2-2.dll liborc-0.4-0.dll libpango-1.0-0.dll libpangocairo-1.0-0.dll libpangoft2-1.0-0.dll libpangowin32-1.0-0.dll libpcre2-8-0.dll libpixman-1-0.dll libpng16-16.dll librsvg-2-2.dll libsharpyuv-0.dll libstdc++-6.dll libthai-0.dll libtiff-6.dll libwebp-7.dll libwinpthread-1.dll libxml2-16.dll libzstd.dll vulkan-1.dll zlib1.dll"

for dll in $DLL_LIST; do
    cp "/ucrt64/bin/$dll" "$PUBLISH_DIR/"
done

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

echo "--- 5. Deploying FFMPEG Windows Binaries ---"
cp -r ./codecs "$PUBLISH_DIR/codecs"

cat <<EOF > "$PUBLISH_DIR/___IMPORTANT Download Dotnet Runtime.url"
[{000214A0-0000-0000-C000-000000000046}]
Prop3=19,11
[InternetShortcut]
URL=https://aka.ms/dotnet/10.0/windowsdesktop-runtime-win-x64.exe
IDList=
IconFile=C:\Windows\System32\shell32.dll
IconIndex=13
EOF

echo "--- DONE ---"
