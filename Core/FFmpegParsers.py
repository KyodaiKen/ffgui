from abc import ABC, abstractmethod
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
        "FLT_MIN": -struct.unpack('f', b'\xff\xff\x7f\x7f')[0],
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
            self._notify(f"\r{status}{clear_line}", progress_callback, end='')

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
    def _create_param_dict(self, name, p_type, flags, parsed, section):
        """Override to only show encoder/decoder booleans."""
        base = super()._create_param_dict(name, p_type, flags, parsed, section)
        for key in ["for_muxer", "for_demuxer"]:
            base.pop(key, None)
        return base

    def parse_list(self):
        output = self._run_cmd(["-codecs"])
        codecs = []
        pattern = re.compile(r"^\s([D.][E.][VASDT.][I.][L.][S.])\s+([\w-]+)\s+(.*)$")
        for line in output.splitlines():
            match = pattern.match(line)
            if match:
                flags, main_name, descr_full = match.groups()
                decoders = re.search(r"\(decoders: ([^)]+)\)", descr_full)
                encoders = re.search(r"\(encoders: ([^)]+)\)", descr_full)
                names = set(decoders.group(1).split() if decoders else []) | set(encoders.group(1).split() if encoders else [])
                if not names: names.add(main_name)
                for name in sorted(list(names)):
                    codecs.append({
                        "name": name, "parent_codec": main_name if name != main_name else None,
                        "descr": descr_full.split('(')[0].strip(),
                        "flags": {"decoder": flags[0] == 'D', "encoder": flags[1] == 'E', "lossy": flags[4] == 'L'}
                    })
        return codecs

    def parse_details(self, item_name):
        output = self._run_cmd(["-h", f"encoder={item_name}"])
        if "Unknown" in output or not output:
            output = self._run_cmd(["-h", f"decoder={item_name}"])

        data = self._parse_av_options(output)
        header_match = re.search(r"(?:Encoder|Decoder)\s+([\w_-]+)", output)
        data["name"] = header_match.group(1) if header_match else item_name
        return data

class FFmpegFormatParser(FFmpegBaseParser):
    def _create_param_dict(self, name, p_type, flags, parsed, section):
        """Override to only show muxer/demuxer booleans."""
        base = super()._create_param_dict(name, p_type, flags, parsed, section)
        for key in ["for_encoder", "for_decoder"]:
            base.pop(key, None)
        return base

    def parse_list(self):
        output = self._run_cmd(["-codecs"])
        codecs_map = {}

        # Pattern: [D.][E.][V.][A.][S.] name description
        pattern = re.compile(r"^\s([D\.])([E\.])([VAS\.])([S\.])([D\.])([T\.])\s+([\w_-]+)\s+(.*)$")

        for line in output.splitlines():
            match = pattern.match(line)
            if match:
                can_dec, can_enc, type_char, draw_horiz, direct_rend, weird_flag, name, descr = match.groups()

                # Use name as primary key to merge Encoder/Decoder info
                if name not in codecs_map:
                    codecs_map[name] = {
                        "name": name,
                        "descr": descr.strip(),
                        "type": {"V": "video", "A": "audio", "S": "subtitle"}.get(type_char, "other"),
                        "is_encoder": False,
                        "is_decoder": False,
                        "capabilities": {
                            "draw_horiz": draw_horiz == 'S',
                            "direct_rend": direct_rend == 'D'
                        }
                    }

                if can_enc == 'E': codecs_map[name]["is_encoder"] = True
                if can_dec == 'D': codecs_map[name]["is_decoder"] = True

        return list(codecs_map.values())

    def parse_details(self, item_name):
        # Codecs don't have "extensions" like formats, but they have "supported_pix_fmts"
        # or "supported_samplerates" in their help output.
        final = {"name": item_name, "parameters": [], "supported_pix_fmts": [], "supported_sample_rates": []}

        for cmd_type in ["encoder", "decoder"]:
            output = self._run_cmd(["-h", f"{cmd_type}={item_name}"])
            if not output or "Unknown" in output:
                continue

            # Capture supported pixel formats or sample rates
            pix_match = re.search(r"Supported pixel formats: (.*?)\n", output)
            if pix_match:
                fmts = [f.strip() for f in pix_match.group(1).split(' ')]
                final["supported_pix_fmts"] = list(set(final["supported_pix_fmts"] + fmts))

            res = self._parse_av_options(output)
            for p in res["parameters"]:
                existing = next((x for x in final["parameters"] if x["name"] == p["name"] and x["section"] == p["section"]), None)
                if existing:
                    existing["for_encoder"] = existing.get("for_encoder", False) or p.get("for_encoder", False)
                    existing["for_decoder"] = existing.get("for_decoder", False) or p.get("for_decoder", False)
                else:
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

if __name__ == "__main__":
    # Create cache folder if it doesn't exist
    os.makedirs("../.cache", exist_ok=True)

    filter_p = FFmpegFilterParser(disk_cache_file="../.cache/cache_filters.json")
    codec_p  = FFmpegCodecParser(disk_cache_file="../.cache/cache_codecs.json")
    format_p = FFmpegFormatParser(disk_cache_file="../.cache/cache_formats.json")
    pix_p    = FFmpegPixelFormatParser(disk_cache_file="../.cache/cache_pix_fmts.json")

    all_filters = filter_p.get_all()
    all_codecs  = codec_p.get_all()
    all_formats = format_p.get_all()
    all_pix_fmts = pix_p.get_all()

    print(f"\nTotal Filters: {len(all_filters)}")
    print(f"Total Codecs:  {len(all_codecs)}")
    print(f"Total Formats: {len(all_formats)}")
    print(f"Total Pixel Formats: {len(all_pix_fmts)}")
