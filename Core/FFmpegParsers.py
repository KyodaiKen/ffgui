import subprocess
import re
import json
import os
from abc import ABC, abstractmethod

class FFmpegBaseParser(ABC):
    def __init__(self, ffmpeg_path="ffmpeg", disk_cache_file="ffmpeg_cache.json"):
        self.ffmpeg_path = ffmpeg_path
        self.disk_cache_file = disk_cache_file

    def _run_cmd(self, args):
        cmd = [self.ffmpeg_path, "-hide_banner"] + args
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
            return result.stdout
        except FileNotFoundError:
            return ""

    def _get_ffmpeg_version(self):
        try:
            result = subprocess.run([self.ffmpeg_path, "-version"], capture_output=True, text=True, encoding='utf-8', errors='ignore')
            return result.stdout.strip()
        except FileNotFoundError:
            return "unknown"

    def _load_cache(self):
        if os.path.exists(self.disk_cache_file):
            try:
                with open(self.disk_cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return None
        return None

    def _save_cache(self, version_str, data):
        payload = {"ffmpeg_version": version_str, "data": data}
        with open(self.disk_cache_file, 'w', encoding='utf-8') as f:
            json.dump(payload, f, indent=2)

    @abstractmethod
    def parse_list(self):
        """Should return a list of dicts with basic info (name, descr, etc.)"""
        pass

    @abstractmethod
    def parse_details(self, item_name):
        """Should return the parameters/AVOptions for a specific item."""
        pass

    def get_all(self, force_refresh=False):
        current_version = self._get_ffmpeg_version()
        cache = self._load_cache()

        if not force_refresh and cache and cache.get("ffmpeg_version") == current_version:
            return cache.get("data", [])

        print(f"Refreshing cache for {self.__class__.__name__}...")
        items = self.parse_list()
        for i, item in enumerate(items):
            print(f"  > [{i+1}/{len(items)}] {item['name']}", end='\r')
            item['parameters'] = self.parse_details(item['name'])

        print(f"\nFinished. Saving to {self.disk_cache_file}")
        self._save_cache(current_version, items)
        return items

    def _parse_av_options(self, output):
        """Common helper to parse the AVOptions table found in almost all FFmpeg help outputs."""
        params = []
        # Matches:   name <type> flags description
        param_pattern = re.compile(r"^\s{2,4}([\w_-]+)\s+<([^>]+)>\s+[.A-Z]+\s+(.*)$")
        # Matches:   option value flags description
        option_pattern = re.compile(r"^\s{5,6}([\w_-]+)\s+([\d.-x]+|[\w-]+)\s+[.A-Z]+\s*(.*)$")

        current_param = None
        for line in output.splitlines():
            p_match = param_pattern.match(line)
            if p_match:
                name, p_type, descr = p_match.groups()
                current_param = {"name": name, "type": f"<{p_type}>", "descr": descr.strip(), "options": []}
                params.append(current_param)
                continue

            o_match = option_pattern.match(line)
            if o_match and current_param:
                opt_name, opt_val, opt_descr = o_match.groups()
                current_param["options"].append({"name": opt_name, "descr": opt_descr.strip() or opt_val})
        return params

class FFmpegFilterParser(FFmpegBaseParser):
    def parse_list(self):
        output = self._run_cmd(["-filters"])
        filters = []
        pattern = re.compile(r"^\s([T.][S.][C.])\s+([\w]+)\s+([AVN|]+->[AVN|]+|->[AVN|]+|[AVN|]+->)\s+(.*)$")

        for line in output.splitlines():
            match = pattern.match(line)
            if match:
                flags, name, io, descr = match.groups()
                in_p, out_p = io.split("->")
                filters.append({
                    "name": name, "descr": descr.strip(), "inputs": in_p or None, "outputs": out_p or None,
                    "type": "V" if "V" in io else "A" if "A" in io else "N" if "N" in io else "|",
                    "flags": {"timeline": flags[0]=='T', "slice_threading": flags[1]=='S', "command": flags[2]=='C'}
                })
        return filters

    def parse_details(self, item_name):
        output = self._run_cmd(["-h", f"filter={item_name}"])
        return self._parse_av_options(output)

class FFmpegCodecParser(FFmpegBaseParser):
    def parse_list(self):
        """Parses the output of ffmpeg -codecs."""
        output = self._run_cmd(["-codecs"])
        codecs = []

        # Updated Regex:
        # ^\s           -> Leading space
        # ([D.][E.][VASDT.][I.][L.][S.]) -> 6 specific flag slots
        # \s+           -> Space separator
        # ([\w-]+)      -> The codec name (allows letters, numbers, underscores, hyphens)
        # \s+           -> Space separator
        # (.*)$         -> The description
        pattern = re.compile(r"^\s([D.][E.][VASDT.][I.][L.][S.])\s+([\w-]+)\s+(.*)$")

        for line in output.splitlines():
            match = pattern.match(line)
            if match:
                flags, name, descr = match.groups()

                # Determine the primary type
                type_char = flags[2]
                type_map = {
                    'V': 'Video',
                    'A': 'Audio',
                    'S': 'Subtitle',
                    'D': 'Data',
                    'T': 'Attachment'
                }

                codecs.append({
                    "name": name,
                    "descr": descr.strip(),
                    "type": type_map.get(type_char, "Unknown"),
                    "flags": {
                        "decoder": flags[0] == 'D',
                        "encoder": flags[1] == 'E',
                        "intra_only": flags[3] == 'I',
                        "lossy": flags[4] == 'L',
                        "lossless": flags[5] == 'S'
                    },
                    "parameters": []
                })
        return codecs

    def parse_details(self, item_name):
        """
        Codecs are unique because one 'codec' entry might have multiple
        specialized encoders (e.g., av1 has libaom-av1, libsvtav1, etc.).
        This method tries the base codec help first.
        """
        # Try generic encoder help
        output = self._run_cmd(["-h", f"encoder={item_name}"])
        if "Unknown" in output or not output:
            # Fallback to decoder help
            output = self._run_cmd(["-h", f"decoder={item_name}"])

        return self._parse_av_options(output)

class FFmpegFormatParser(FFmpegBaseParser):
    def parse_list(self):
        """Parses the output of ffmpeg -formats."""
        output = self._run_cmd(["-formats"])
        formats = []

        # Pattern for:  DE mp4             MP4 (MPEG-4 Part 14)
        # Flags: D (Demuxing), E (Muxing)
        pattern = re.compile(r"^\s([D.][E.])\s+([\w,]+)\s+(.*)$")

        for line in output.splitlines():
            match = pattern.match(line)
            if match:
                flags, name, descr = match.groups()
                # Some names are comma-separated aliases, e.g., "mov,mp4,m4a,3gp,3g2,mj2"
                primary_name = name.split(',')[0]

                formats.append({
                    "name": name,
                    "primary_name": primary_name,
                    "descr": descr.strip(),
                    "capabilities": {
                        "demuxing": flags[0] == 'D',
                        "muxing": flags[1] == 'E'
                    }
                })
        return formats

    def parse_details(self, item_name):
        """
        Parses ffmpeg -h muxer=... and demuxer=...
        We use the primary_name to ensure we get the correct help page.
        """
        primary_name = item_name.split(',')[0]
        params = []

        # Try to get Muxer options
        mux_out = self._run_cmd(["-h", f"muxer={primary_name}"])
        if "Unknown" not in mux_out:
            params.extend(self._parse_av_options(mux_out))

        # Try to get Demuxer options (avoiding duplicates if they share the same help)
        demux_out = self._run_cmd(["-h", f"demuxer={primary_name}"])
        if "Unknown" not in demux_out and demux_out != mux_out:
            demux_params = self._parse_av_options(demux_out)
            # Simple deduplication by name
            existing_names = {p['name'] for p in params}
            for p in demux_params:
                if p['name'] not in existing_names:
                    params.append(p)

        return params

if __name__ == "__main__":
    # 1. Initialize Parsers with unique cache files
    filter_p = FFmpegFilterParser(disk_cache_file="../.cache/cache_filters.json")
    codec_p  = FFmpegCodecParser(disk_cache_file="../.cache/cache_codecs.json")
    format_p = FFmpegFormatParser(disk_cache_file="../.cache/cache_formats.json")

    # 2. Retrieve Data (Automatically handles -version check and caching)
    all_filters = filter_p.get_all()
    all_codecs  = codec_p.get_all()
    all_formats = format_p.get_all()

    # 3. Quick Data Inspection
    print(f"Total Filters: {len(all_filters)}")
    print(f"Total Codecs:  {len(all_codecs)}")
    print(f"Total Formats: {len(all_formats)}")

    # Search example for MP4 format
    mp4 = next((f for f in all_formats if "mp4" in f['name']), None)
    if mp4:
        print(f"\nFormat: {mp4['descr']}")
        # Show parameters like 'movflags' or 'faststart' if they exist
        param_names = [p['name'] for p in mp4['parameters']]
        print(f"Parameters found: {', '.join(param_names[:10])}...")
