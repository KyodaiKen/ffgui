from abc import ABC, abstractmethod
from datetime import timedelta
from fractions import Fraction
import subprocess
import sys
import struct
import re
import os
import json

class FFmpegBaseParser(ABC):
    # Mapping FFmpeg/C constants to Python numbers
    _NUMERIC_LIMITS = {
        "INT_MIN": -2147483648,
        "INT_MAX": 2147483647,
        "UINT32_MAX": 4294967295,
        "I64_MIN": -9223372036854775808,
        "I64_MAX": 9223372036854775807,
        # Use struct to get exact IEEE 754 single-precision (float) limits
        "-FLT_MAX": -struct.unpack('f', b'\xff\xff\x7f\x7f')[0],
        "FLT_MAX": struct.unpack('f', b'\xff\xff\x7f\x7f')[0],
        # Double precision limits from Python's own float info
        "DBL_MIN": -sys.float_info.max,
        "DBL_MAX": sys.float_info.max,
        # Common FFmpeg semantic aliases
        "auto": -1,
        "none": 0,
        "disable": 0,
        "false": 0,
        "true": 1
    }

    def _to_num(self, val):
        """Converts strings and FFmpeg constants to exact numeric types."""
        if val is None:
            return None

        # Standardize for lookup
        s_val = val.strip()
        lookup = s_val.upper()

        # 1. Resolve Constants
        if lookup in self._NUMERIC_LIMITS:
            return self._NUMERIC_LIMITS[lookup]

        # 2. Try Numeric Conversion
        try:
            # Handle Hexadecimal
            if s_val.lower().startswith('0x'):
                return int(s_val, 16)

            # Handle float/int (Scientific notation like 1e+08 is handled by float())
            num = float(s_val)
            # Return as int if it's a whole number to keep JSON clean (e.g., 5.0 -> 5)
            return int(num) if num.is_integer() else num
        except ValueError:
            # Fallback for strings that aren't numbers (like 'auto' if not in map)
            return s_val

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
        output = self._run_cmd(["-version"])
        return output if output else "unknown"

    def _load_cache(self):
        if os.path.exists(self.disk_cache_file):
            try:
                with open(self.disk_cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return None
        return None

    def _save_cache(self, version_str, data):
        os.makedirs(os.path.dirname(self.disk_cache_file) or '.', exist_ok=True)
        payload = {"ffmpeg_version": version_str, "data": data}
        with open(self.disk_cache_file, 'w', encoding='utf-8') as f:
            json.dump(payload, f, indent=2)

    def _notify(self, message, callback, end='\n'):
        if callback:
            callback(message + end)
        else:
            print(f"{message}", end=end, flush=True)

    def get_all(self, force_refresh=False, progress_callback=None):
        current_version = self._get_ffmpeg_version()
        cache = self._load_cache()

        if not force_refresh and cache and cache.get("ffmpeg_version") == current_version:
            self._notify(f"Using cached data for {self.__class__.__name__}", progress_callback)
            return cache.get("data", [])

        self._notify(f"Refreshing cache for {self.__class__.__name__}...", progress_callback)
        items = self.parse_list()
        clear_line = "\033[K"

        for i, item in enumerate(items):
            status = f"  > [{i+1}/{len(items)}] {item['name']}"
            self._notify(f"\r{status}{clear_line}", progress_callback, end='') # Triggers granular_callback

            details = self.parse_details(item['name'])
            if isinstance(details, dict):
                item.update(details)
            else:
                item['parameters'] = details

        self._notify(f"\nFinished {self.__class__.__name__}. Saving cache.", progress_callback)
        self._save_cache(current_version, items)
        return items

    def _clean_descr(self, raw_descr):
        # 1. Extract metadata strings
        min_match = re.search(r"from (.*?) to", raw_descr)
        max_match = re.search(r"to (.*?)\)", raw_descr)
        def_match = re.search(r"default (.*?)\)", raw_descr)

        # 2. Extract and convert to numbers
        min_v = self._to_num(min_match.group(1)) if min_match else None
        max_v = self._to_num(max_match.group(1)) if max_match else None
        def_v = self._to_num(def_match.group(1)) if def_match else None

        # 3. Clean description text
        clean = re.sub(r"\(from.*?default.*?\)", "", raw_descr).strip()
        # Strip flag artifacts from the start
        clean = re.sub(r"^[A-Z]\.\s+", "", clean)
        clean = re.sub(r"^[EDVASFTR\.]{2,}\s*", "", clean)

        return {
            "clean_descr": clean.strip(),
            "min": min_v,
            "max": max_v,
            "default": def_v
        }

    def _map_flags(self, flag_str):
        """Extended mapping to capture Timeline and other flags."""
        if not flag_str or len(flag_str) < 5:
            return {}

        # Standard FFmpeg flag positions
        return {
            "encoding": 'E' in flag_str[0:2],
            "decoding": 'D' in flag_str[0:2],
            "filtering": 'F' in flag_str[2] if len(flag_str) > 2 else False,
            "video": 'V' in flag_str[3] if len(flag_str) > 3 else False,
            "audio": 'A' in flag_str[4] if len(flag_str) > 4 else False,
            "timeline": 'T' in flag_str,
            "runtime": 'R' in flag_str
        }

    def _create_param_dict(self, name, p_type, flags, parsed, section):
        """Builds the final dictionary with numeric values and clean types."""
        f_map = self._map_flags(flags)

        # Strip the < > from type
        clean_type = p_type.replace('<', '').replace('>', '')

        return {
            "name": name,
            "section": section,
            "type": clean_type,
            "is_flags": clean_type == "flags",
            "descr": parsed["clean_descr"],
            "context": f_map,
            "min": parsed["min"],
            "max": parsed["max"],
            "default": parsed["default"],
            "options": []
        }

    def _parse_av_options(self, output):
        data = {"parameters": []}
        param_pattern = re.compile(r"^\s{1,4}-?([\w_-]+)\s+<([^>]+)>\s+([EDVASFTR\.]{5,})\s*(.*)$")
        option_pattern = re.compile(r"^\s{5,14}([\w_-]+)\s+(-?\d+|0x[\da-fA-F]+)\s+([EDVASFTR\.]{5,})\s*(.*)$")
        section_pattern = re.compile(r"^([\w\s\(2\)]+)\s+AVOptions:$")

        current_param = None
        current_section = "General"

        for line in output.splitlines():
            # Track sections (e.g. SWScaler, framesync)
            s_match = section_pattern.match(line)
            if s_match:
                current_section = s_match.group(1).strip()
                continue

            p_match = param_pattern.match(line)
            if p_match:
                name, p_type, flags, raw_descr = p_match.groups()
                parsed = self._clean_descr(raw_descr)
                current_param = self._create_param_dict(name, p_type, flags, parsed, current_section)
                data["parameters"].append(current_param)
                continue

            o_match = option_pattern.match(line)
            if o_match and current_param:
                opt_name, opt_val, opt_flags, opt_descr = o_match.groups()
                current_param["options"].append({
                    "name": opt_name,
                    "value": self._to_num(opt_val), # Use the numeric converter here!
                    "descr": opt_descr.strip(),
                    "context": self._map_flags(opt_flags)
                })
        return data

class FFmpegGlobalsParser(FFmpegBaseParser):
    def __init__(self, ffmpeg_path="ffmpeg", disk_cache_file="cache.json", **kwargs):
        super().__init__(ffmpeg_path, disk_cache_file, **kwargs)
        self._full_help_output = None
        self._header_to_section = {
            "Video options": "video",
            "Advanced Video options": "video",
            "Audio options": "audio",
            "Advanced Audio options": "audio",
            "Subtitle options": "subtitle",
            "Advanced Subtitle options": "subtitle"
        }

    def parse_list(self):
        return [{"name": "video"}, {"name": "audio"}, {"name": "subtitle"}, {"name": "av_options"}]

    def _determine_target_sections(self, current_section, flags):
        """Returns a list of all applicable sections for a given parameter."""
        # If we are in a specific header (e.g., 'Video options'), keep it pinned
        if current_section != "av_options":
            return [current_section]

        targets = []
        if "V" in flags: targets.append("video")
        if "A" in flags: targets.append("audio")
        if "S" in flags: targets.append("subtitle")

        # If no specific media flags are found, default to general av_options
        return targets if targets else ["av_options"]

    def parse_details(self, section_name):
        if not self._full_help_output:
            self._full_help_output = self._run_cmd(["-h", "full"])

        params = []
        av_pattern = re.compile(r"^\s{1,4}-([\w:-]+)\s+<([^>]+)>\s+([EDVASFTR\.]{5,})\s*(.*)$")
        std_pattern = re.compile(r"^\s{1,4}-([\w:-]+)\s+([\w\s]+?)\s{2,}(.*)$")
        opt_pattern = re.compile(r"^\s{5,14}([\w_-]+)\s+(-?\d+|0x[\da-fA-F]+)\s+([EDVASFTR\.]{5,})\s*(.*)$")

        current_header_section = None
        last_param = None
        processing_av_options = False

        for line in self._full_help_output.splitlines():
            if not line.strip():
                continue

            # 1. Section Header Detection
            if line.endswith(":") or "AVOptions" in line:
                header = line.strip().rstrip(":")
                if processing_av_options and "AVOptions" in line and "AVCodecContext" not in line:
                    break
                if "AVCodecContext AVOptions" in line:
                    processing_av_options = True

                current_header_section = self._header_to_section.get(header, "av_options") if "AVOptions" not in header else "av_options"
                last_param = None
                continue

            # 2. Parameter Parsing
            av_match = av_pattern.match(line)
            std_match = std_pattern.match(line)

            if av_match or std_match:
                if av_match:
                    name, p_type, flags, raw_descr = av_match.groups()
                    # Determine ALL sections this parameter belongs to
                    targets = self._determine_target_sections(current_header_section, flags)

                    # Check if the currently requested section is in the list
                    if section_name in targets:
                        parsed = self._clean_descr(raw_descr)
                        last_param = self._create_param_dict(name, p_type, flags, parsed, section_name)
                        params.append(last_param)
                    else:
                        last_param = None
                else:
                    # Standard parameters (usually from specific headers like 'Video options')
                    name, p_type, descr = std_match.groups()
                    if current_header_section == section_name:
                        parsed = {"clean_descr": descr.strip(), "min": None, "max": None, "default": None}
                        last_param = self._create_param_dict(name, p_type, ".....", parsed, section_name)
                        params.append(last_param)
                    else:
                        last_param = None
                continue

            # 3. Choice/Option Parsing
            opt_match = opt_pattern.match(line)
            if opt_match and last_param:
                if not line.strip().startswith("-"):
                    o_name, o_val, o_flags, o_descr = opt_match.groups()
                    last_param["options"].append({
                        "name": o_name,
                        "value": self._to_num(o_val),
                        "descr": o_descr.strip(),
                        "context": self._map_flags(o_flags)
                    })

        return {"parameters": params}

class FFmpegFilterParser(FFmpegBaseParser):
    def _create_param_dict(self, name, p_type, flags, parsed, section):
            """Override to remove muxer/encoder booleans for filters."""
            base = super()._create_param_dict(name, p_type, flags, parsed, section)
            # Remove keys not relevant to filters
            for key in ["for_muxer", "for_demuxer", "for_encoder", "for_decoder"]:
                base.pop(key, None)
            return base

    def parse_list(self):
        output = self._run_cmd(["-filters"])
        filters = []
        # [T.S.C] name description
        pattern = re.compile(r"^\s([T.][S.][C.])\s+([\w]+)\s+([AVN|]*->[AVN|]*)\s+(.*)$")
        for line in output.splitlines():
            match = pattern.match(line)
            if match:
                flags_raw, name, io_map, descr = match.groups()
                filters.append({
                    "name": name,
                    "descr": descr.strip(),
                    "is_dynamic": "dynamic" in io_map,
                    "flags": {
                        "timeline": flags_raw[0] == 'T',
                        "slice_threading": flags_raw[1] == 'S',
                        "command_support": flags_raw[2] == 'C'
                    }
                })
        return filters

    def parse_details(self, item_name):
        output = self._run_cmd(["-h", f"filter={item_name}"])
        header_match = re.search(r"Filter\s+([\w_-]+)", output)
        data = self._parse_av_options(output)
        data["name"] = header_match.group(1) if header_match else item_name
        return data

class FFmpegCodecParser(FFmpegBaseParser):
    def parse_list(self):
        output = self._run_cmd(["-codecs"])
        codec_map = {}
        # We track which names were identified as 'parents' (rogue names) to exclude them
        rogue_names = set()

        # Regex captures: 1. Flags, 2. Name, 3. Description
        pattern = re.compile(r"^\s([D.E.VASDT.ILS.]{6})\s+([\w-]+)\s+(.*)$")

        for line in output.splitlines():
            match = pattern.match(line)
            if not match:
                continue

            flags_raw, main_name, descr_full = match.groups()

            # Identify bracketed wrappers
            dec_match = re.search(r"\(decoders:\s*([^)]+)\)", descr_full)
            enc_match = re.search(r"\(encoders:\s*([^)]+)\)", descr_full)

            # CLEANING LOGIC:
            # If brackets exist, main_name (e.g., 'av1') is a rogue name and MUST be excluded.
            if dec_match or enc_match:
                rogue_names.add(main_name)

                # Process actual usable handlers from brackets
                line_handlers = []
                if dec_match:
                    for d in dec_match.group(1).split():
                        line_handlers.append({"name": d, "is_dec": True, "is_enc": False})
                if enc_match:
                    for e in enc_match.group(1).split():
                        line_handlers.append({"name": e, "is_dec": False, "is_enc": True})

                for h in line_handlers:
                    name = h["name"]
                    # Clean description: remove everything from the first bracket
                    clean_descr = descr_full.split('(')[0].strip()

                    if name not in codec_map:
                        codec_map[name] = {
                            "name": name,
                            "descr": clean_descr,
                            "flags": {
                                "decoder": h["is_dec"], "encoder": h["is_enc"],
                                "video": flags_raw[2] == 'V', "audio": flags_raw[2] == 'A',
                                "subtitle": flags_raw[2] == 'S', "lossy": flags_raw[4] == 'L'
                            }
                        }
                    else:
                        codec_map[name]["flags"]["decoder"] |= h["is_dec"]
                        codec_map[name]["flags"]["encoder"] |= h["is_enc"]
            else:
                # No brackets: The main name is a legitimate standalone codec (like wmav1)
                # Only add if it hasn't been flagged as a rogue name earlier
                if main_name not in rogue_names:
                    codec_map[main_name] = {
                        "name": main_name,
                        "descr": descr_full.strip(),
                        "flags": {
                            "decoder": flags_raw[0] == 'D', "encoder": flags_raw[1] == 'E',
                            "video": flags_raw[2] == 'V', "audio": flags_raw[2] == 'A',
                            "subtitle": flags_raw[2] == 'S', "lossy": flags_raw[4] == 'L'
                        }
                    }

        # FINAL GUARD: Remove any name that was ever flagged as a rogue/parent name
        for rogue in rogue_names:
            codec_map.pop(rogue, None)

        return sorted(list(codec_map.values()), key=lambda x: x["name"])

    def parse_details(self, item_name):
        """Probes parameters only for the filtered list of valid handlers."""
        output = self._run_cmd(["-h", f"encoder={item_name}"])
        if "Unknown" in output or not output.strip():
            output = self._run_cmd(["-h", f"decoder={item_name}"])

        if not output or "Unknown" in output:
            return {"parameters": []}

        return self._parse_av_options(output)

class FFmpegFormatParser(FFmpegBaseParser):
    def _create_param_dict(self, name, p_type, flags, parsed, section):
        """Override to only show muxer/demuxer booleans."""
        base = super()._create_param_dict(name, p_type, flags, parsed, section)
        for key in ["for_encoder", "for_decoder"]:
            base.pop(key, None)
        return base

    def parse_list(self):
        # FIX 1: Run -formats, not -codecs
        output = self._run_cmd(["-formats"])
        formats_map = {}

        # FIX 2: Correct Regex for -formats output
        # Pattern: [D ][E ] name description
        pattern = re.compile(r"^\s([D\s])([E\s])\s+([\w,]+)\s+(.*)$")

        for line in output.splitlines():
            match = pattern.match(line)
            if match:
                can_demux, can_mux, name_str, descr = match.groups()

                # Formats often have multiple names: "matroska,webm"
                names = name_str.split(',')
                primary_id = names[0]

                if primary_id not in formats_map:
                    formats_map[primary_id] = {
                        "name": primary_id,
                        "aliases": names[1:],
                        "descr": descr.strip(),
                        "is_demuxer": False,
                        "is_muxer": False
                    }

                if can_demux == 'D': formats_map[primary_id]["is_demuxer"] = True
                if can_mux == 'E':   formats_map[primary_id]["is_muxer"] = True

        return list(formats_map.values())

    def parse_details(self, item_name):
        # FIX 3: Details for formats use -h muxer= and -h demuxer=
        final = {"name": item_name, "parameters": [], "extensions": []}

        for cmd_type in ["muxer", "demuxer"]:
            output = self._run_cmd(["-h", f"{cmd_type}={item_name}"])
            if not output or "Unknown" in output:
                continue

            # Extra metadata parsing for formats
            ext_match = re.search(r"Common extensions: (.*?)\.", output)
            if ext_match:
                exts = [e.strip() for e in ext_match.group(1).split(',')]
                final["extensions"] = list(set(final.get("extensions", []) + exts))

            res = self._parse_av_options(output)
            for p in res["parameters"]:
                # Check for duplicates across muxer/demuxer details
                existing = next((x for x in final["parameters"] if x["name"] == p["name"]), None)
                if not existing:
                    final["parameters"].append(p)

        return final

class FFmpegPixelFormatParser(FFmpegBaseParser):
    def parse_list(self):
        output = self._run_cmd(["-pix_fmts"])
        pix_fmts = []
        pattern = re.compile(r"^([IOHBP.]{5})\s+([\w-]+)\s+(\d+)\s+(\d+)\s+([\d-]+)$")

        start_parsing = False
        for line in output.splitlines():
            if "-----" in line:
                start_parsing = True
                continue
            if not start_parsing: continue
            match = pattern.match(line)
            if match:
                flags, name, nb_components, bpp, depths = match.groups()
                pix_fmts.append({
                    "name": name, "nb_components": int(nb_components), "bits_per_pixel": int(bpp),
                    "bit_depths": [int(d) for d in depths.split('-') if d.isdigit()],
                    "flags": {
                        "input_supported": flags[0] == 'I', "output_supported": flags[1] == 'O',
                        "hw_accelerated": flags[2] == 'H', "paletted": flags[3] == 'P', "bitstream": flags[4] == 'B'
                    }
                })
        return pix_fmts

    def parse_details(self, item_name):
        return {"parameters": [], "capabilities": {}, "supports": {}}

class FFmpegMediaInfoParser:
    def __init__(self, ffprobe_path, probe_size=26214400, analyze_duration=120000000):
        self.probe_size = probe_size
        self.analyze_duration = analyze_duration
        self.ffprobe_path = ffprobe_path

    def get_info(self, filename):
        cmd = [
            self.ffprobe_path,
            "-probesize", str(self.probe_size),
            "-analyzeduration", str(self.analyze_duration),
            "-v", "quiet",
            "-of", "json",
            "-show_streams",
            "-show_format",
            filename
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            raw_data = json.loads(result.stdout)
            return self._refine_data(raw_data)
        except Exception as e:
            return {"error": str(e)}

    def _to_fraction(self, value_str):
        """Safely converts '60000/1001' or '16:9' to a Fraction."""
        if not value_str or value_str in ("0/0", "0:0"):
            return None
        try:
            # Handle both colon (16:9) and slash (16/9) separators
            normalized = value_str.replace(":", "/")
            return Fraction(normalized)
        except (ValueError, ZeroDivisionError):
            return None

    def _to_timedelta(self, value_str):
        """Converts second strings (e.g. '338.070375') to timedelta."""
        if value_str is None:
            return None
        try:
            return timedelta(seconds=float(value_str))
        except ValueError:
            return None

    def _refine_data(self, data):
        # 1. Refine Format (Container) level
        if "format" in data:
            f = data["format"]
            f["td_duration"] = self._to_timedelta(f.get("duration"))
            f["td_start_time"] = self._to_timedelta(f.get("start_time"))

        # 2. Refine Streams
        if "streams" in data:
            for stream in data["streams"]:
                # Duration/Time handling
                stream["td_duration"] = self._to_timedelta(stream.get("duration"))
                stream["td_start_time"] = self._to_timedelta(stream.get("start_time"))

                # Fraction Conversions
                for key in ["r_frame_rate", "avg_frame_rate", "time_base"]:
                    if key in stream:
                        stream[f"frac_{key}"] = self._to_fraction(stream[key])

                # Display Aspect Ratio (DAR) Logic
                if stream.get("codec_type") == "video":
                    # Priority 1: Use the existing display_aspect_ratio from JSON
                    dar_str = stream.get("display_aspect_ratio")
                    dar_frac = self._to_fraction(dar_str)

                    # Priority 2: Calculate if DAR is missing or invalid
                    if dar_frac is None:
                        width = stream.get("width")
                        height = stream.get("height")
                        if width and height:
                            dar_frac = Fraction(width, height)
                            # Apply SAR if available
                            sar_str = stream.get("sample_aspect_ratio")
                            sar_frac = self._to_fraction(sar_str)
                            if sar_frac:
                                dar_frac *= sar_frac

                    stream["frac_display_aspect_ratio"] = dar_frac

                # Numeric Casting for clean JSON
                for key in ["bit_rate", "nb_frames", "width", "height"]:
                    if key in stream and isinstance(stream[key], str):
                        try:
                            stream[key] = int(stream[key])
                        except ValueError: pass

        return data



if __name__ == "__main__":
    # Create cache folder if it doesn't exist
    os.makedirs(".cache", exist_ok=True)

    globals_p = FFmpegGlobalsParser(disk_cache_file=".cache/ffmpeg/globals.json")
    filter_p = FFmpegFilterParser(disk_cache_file=".cache/ffmpeg/filters.json")
    codec_p  = FFmpegCodecParser(disk_cache_file=".cache/ffmpeg/codecs.json")
    format_p = FFmpegFormatParser(disk_cache_file=".cache/ffmpeg/formats.json")
    pix_p    = FFmpegPixelFormatParser(disk_cache_file=".cache/ffmpeg/pix_fmts.json")

    all_globals = globals_p.get_all()
    all_codecs  = codec_p.get_all()
    all_pix_fmts = pix_p.get_all()
    all_formats = format_p.get_all()
    all_filters = filter_p.get_all()

    print(f"\nTotal Globals:     {len(all_globals)}")
    print(f"Total Codecs:        {len(all_codecs)}")
    print(f"Total Pixel Formats: {len(all_pix_fmts)}")
    print(f"Total Formats:       {len(all_formats)}")
    print(f"Total Filters:       {len(all_filters)}")
