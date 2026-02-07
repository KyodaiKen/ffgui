#!/bin/bash

# Configuration
BASE_URL="https://raw.githubusercontent.com/gircore/gir-files/main/windows"
UCRT_BIN="/ucrt64/bin"
START_GIRS=("Gtk-4.0" "Gio-2.0")

# State tracking
processed_girs=()
discovered_dlls=()

function is_processed() {
    local e match="$1"
    for e in "${processed_girs[@]}"; do [[ "$e" == "$match" ]] && return 0; done
    return 1
}

function extract_dependencies() {
    local gir_name="$1"
    if is_processed "$gir_name"; then return; fi
    processed_girs+=("$gir_name")

    echo "--> Analyzing GIR: $gir_name..." >&2

    local raw_content
    raw_content=$(curl -sL -f -r 0-65536 "$BASE_URL/$gir_name.gir")

    if [[ $? -ne 0 || -z "$raw_content" ]]; then
        echo "    [!] Could not fetch $gir_name.gir" >&2
        return
    fi

    # Extract Shared Libraries
    while read -r dll; do
        [[ -n "$dll" ]] && discovered_dlls+=("$dll")
    done < <(echo "$raw_content" | grep -oP 'shared-library="\K[^"]+' | tr ',' '\n')

    # Extract Includes
    while read -r sub_gir; do
        [[ -n "$sub_gir" ]] && extract_dependencies "$sub_gir"
    done < <(echo "$raw_content" | grep -oP '<include\s+name="[^"]+"\s+version="[^"]+"' | \
             sed -E 's/.*name="([^"]*)".*version="([^"]*)".*/\1-\2/')
}

# --- STAGE 1: GIR Discovery ---
echo "Stage 1: Discovering GObject-level DLLs..." >&2
for root in "${START_GIRS[@]}"; do
    extract_dependencies "$root"
done

# --- STAGE 2: Binary Deep Scan ---
echo -e "\nStage 2: Scanning for system dependencies via ntldd..." >&2
FINAL_LIST=()

# Deduplicate Stage 1 list first
unique_gir_dlls=($(printf "%s\n" "${discovered_dlls[@]}" | sort -u))

for dll in "${unique_gir_dlls[@]}"; do
    dll_path="$UCRT_BIN/$dll"
    if [[ -f "$dll_path" ]]; then
        # Add the main DLL
        FINAL_LIST+=("$dll")

        # Use sed to capture everything between "=> " and " ("
        # This is much more reliable than awk columns
        while read -r win_path; do
            if [[ -n "$win_path" ]]; then
                # Convert to unix path and get basename
                unix_path=$(cygpath -u "$win_path")
                # Only keep it if it's in our ucrt64 directory
                if [[ "$unix_path" == *"/ucrt64/"* ]]; then
                    FINAL_LIST+=("$(basename "$unix_path")")
                fi
            fi
        done < <(ntldd -R "$dll_path" | grep -i "ucrt64" | sed -n 's/.*=> \(.*\) (.*/\1/p')
    fi
done

# Final Cleanup: Deduplicate and format
DLL_LIST=$(printf "%s\n" "${FINAL_LIST[@]}" | sort -u | xargs)

echo "---" >&2
echo "Discovery complete." >&2
echo "DLL_LIST=\"$DLL_LIST\""
