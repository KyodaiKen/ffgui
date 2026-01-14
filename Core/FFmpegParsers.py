from abc import ABC, abstractmethod
from datetime import timedelta
from fractions import Fraction
import platform
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
        "-FLT_MAX": -struct.unpack('f', b'\xff\xff\x7f\x7f')[0],
        "FLT_MAX": struct.unpack('f', b'\xff\xff\x7f\x7f')[0],
        "DBL_MIN": -sys.float_info.max,
        "DBL_MAX": sys.float_info.max,
        "auto": -1,
        "none": 0,
        "disable": 0,
        "false": 0,
        "true": 1
    }

    def _to_num(self, val):
        """Converts strings and FFmpeg constants to exact numeric types."""
        if val is None: return None
        s_val = val.strip()
        lookup = s_val.upper()
        if lookup in self._NUMERIC_LIMITS:
            return self._NUMERIC_LIMITS[lookup]
        try:
            if s_val.lower().startswith('0x'):
                return int(s_val, 16)
            num = float(s_val)
            return int(num) if num.is_integer() else num
        except ValueError:
            return s_val

    def __init__(self, ffmpeg_path="ffmpeg", disk_cache_file="ffmpeg_cache.json"):
        self.ffmpeg_path = ffmpeg_path
        self.disk_cache_file = disk_cache_file

    def _run_cmd(self, args):
        cmd = [self.ffmpeg_path, "-hide_banner"] + args
        try:
            flags = 0
            if os.name != 'nt':
                flags = 0x08000000 # CREATE_NO_WINDOW
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', creationflags=flags, errors='ignore')
            return result.stdout
        except FileNotFoundError: return ""

    def _get_ffmpeg_version(self):
        output = self._run_cmd(["-version"])
        return output if output else "unknown"

    def _load_cache(self):
        if os.path.exists(self.disk_cache_file):
            try:
                with open(self.disk_cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError): return None
        return None

    def _save_cache(self, version_str, data):
        """Saves as compact JSON and handles strict NaN compliance."""
        def clean_nan(item):
            import math
            if isinstance(item, list): return [clean_nan(i) for i in item]
            elif isinstance(item, dict): return {k: clean_nan(v) for k, v in item.items()}
            elif isinstance(item, float) and math.isnan(item): return "NaN"
            return item

        os.makedirs(os.path.dirname(self.disk_cache_file) or '.', exist_ok=True)
        cleaned_payload = clean_nan({"ffmpeg_version": version_str, "data": data})

        with open(self.disk_cache_file, 'w', encoding='utf-8') as f:
            # separators removes whitespace for minimum file size
            json.dump(cleaned_payload, f, separators=(',', ':'))

    def _notify(self, message, callback, end='\n'):
        if callback: callback(message + end)
        else: print(f"{message}", end=end, flush=True)

    def get_all(self, force_refresh=False, progress_callback=None):
        current_version = self._get_ffmpeg_version()
        cache = self._load_cache()

        if not force_refresh and cache and cache.get("ffmpeg_version") == current_version:
            self._notify(f"Using cached data for {self.__class__.__name__}", progress_callback)
            return cache.get("data", [])

        self._notify(f"Refreshing cache for {self.__class__.__name__}...", progress_callback)
        items = self.parse_list()
        
        for i, item in enumerate(items):
            self._notify(f"\r  > [{i+1}/{len(items)}] {item['name']}\033[K", progress_callback, end='')
            details = self.parse_details(item['name'])
            if isinstance(details, dict): item.update(details)
            else: item['parameters'] = details

        self._notify(f"\nFinished {self.__class__.__name__}. Saving cache.", progress_callback)
        self._save_cache(current_version, items)
        return items

    def _clean_descr(self, raw_descr):
        min_match = re.search(r"from (.*?) to", raw_descr)
        max_match = re.search(r"to (.*?)\)", raw_descr)
        def_match = re.search(r"default (.*?)\)", raw_descr)
        min_v = self._to_num(min_match.group(1)) if min_match else None
        max_v = self._to_num(max_match.group(1)) if max_match else None
        def_v = self._to_num(def_match.group(1)) if def_match else None

        clean = re.sub(r"\(from.*?default.*?\)", "", raw_descr).strip()
        clean = re.sub(r"^[A-Z]\.\s+", "", clean)
        clean = re.sub(r"^[EDVASFTR\.]{2,}\s*", "", clean)
        return {"clean_descr": clean.strip(), "min": min_v, "max": max_v, "default": def_v}

    def _map_flags(self, flag_str):
        if not flag_str or len(flag_str) < 5: return {}
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
        f_map = self._map_flags(flags)
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
        # Param: Matches lines starting with 1-4 spaces and a dash
        param_pattern = re.compile(r"^\s{1,4}-?([\w:-]+)\s+<([^>]+)>\s+([EDVASFTR\.]{5,})\s*(.*)$")
        
        # Option/Choice: Updated to make the numeric value optional
        # Group 1: Name, Group 2: Potential Value, Group 3: Flags, Group 4: Description
        option_pattern = re.compile(r"^\s{3,20}([\w_-]+)(?:\s+([-?\w\.]+))?\s+([EDVASFTR\.]{5,})\s*(.*)$")
        
        section_pattern = re.compile(r"^([\w\s\(2\)]+)\s+AVOptions:$")

        current_param = None
        current_section = "General"

        for line in output.splitlines():
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
                if line.strip().startswith('-'):
                    continue
                    
                opt_name, opt_val, opt_flags, opt_descr = o_match.groups()
                
                # If no value was provided in the output (common for flags), 
                # we default the value to the name or 1
                final_val = self._to_num(opt_val) if opt_val else opt_name

                current_param["options"].append({
                    "name": opt_name,
                    "value": final_val,
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
        
        # Updated for Global Options to match the BaseParser's improved flexibility
        opt_pattern = re.compile(r"^\s{3,20}([\w_-]+)\s+([-?\w\.]+)\s+([EDVASFTR\.]{5,})\s*(.*)$")

        current_header_section = None
        last_param = None

        for line in self._full_help_output.splitlines():
            if not line.strip(): continue

            # Section Header Detection
            if line.endswith(":") or "AVOptions" in line:
                header = line.strip().rstrip(":")
                current_header_section = self._header_to_section.get(header, "av_options")
                last_param = None
                continue

            # Parameter Parsing
            av_match = av_pattern.match(line)
            std_match = std_pattern.match(line)

            if av_match:
                name, p_type, flags, raw_descr = av_match.groups()
                if section_name in self._determine_target_sections(current_header_section, flags):
                    parsed = self._clean_descr(raw_descr)
                    last_param = self._create_param_dict(name, p_type, flags, parsed, section_name)
                    params.append(last_param)
                else:
                    last_param = None
                continue
            
            if std_match:
                name, p_type, descr = std_match.groups()
                if current_header_section == section_name:
                    parsed = {"clean_descr": descr.strip(), "min": None, "max": None, "default": None}
                    last_param = self._create_param_dict(name, p_type, ".....", parsed, section_name)
                    params.append(last_param)
                else:
                    last_param = None
                continue

            # Choice/Option Parsing for Globals
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
    def __init__(self, ffmpeg_path="ffmpeg", disk_cache_file="ffmpeg_cache.json"):
        super().__init__(ffmpeg_path, disk_cache_file)
        self._filter_io_map = {}
        self._current_filter_name = None

    def _map_io_types(self, io_part):
        """Maps FFmpeg IO characters to descriptive strings."""
        mapping = {'V': 'video', 'A': 'audio', 'N': 'dynamic'}
        return [mapping[c] for c in io_part if c in mapping]

    def _create_param_dict(self, name, p_type, flags, parsed, section):
        base = super()._create_param_dict(name, p_type, flags, parsed, section)
        
        # Remove keys not relevant to filters
        for key in ["for_muxer", "for_demuxer", "for_encoder", "for_decoder"]:
            base.pop(key, None)

        # Inject IO info and the is_complex flag into the parameter context
        io_info = self._filter_io_map.get(self._current_filter_name, {"inputs": [], "outputs": [], "is_complex": False})
        base["context"]["inputs"] = io_info["inputs"]
        base["context"]["outputs"] = io_info["outputs"]
        base["context"]["is_complex"] = io_info["is_complex"]
        
        return base

    def parse_list(self):
        output = self._run_cmd(["-filters"])
        filters = []
        
        # Changed: The first group now matches 2 or 3 characters ([T.][S.][C.]?)
        # This makes the 'C' column optional.
        pattern = re.compile(r"^\s([T.][S.][C.]?)\s+([\w-]+)\s+([AVN|]*->[AVN|]*)\s+(.*)$")
        
        for line in output.splitlines():
            match = pattern.match(line)
            if match:
                flags_raw, name, io_str, descr = match.groups()
                
                in_part, out_part = io_str.split('->')
                inputs = self._map_io_types(in_part)
                outputs = self._map_io_types(out_part)
                
                is_complex = len(inputs) > 1 or len(outputs) > 1 or "N" in io_str

                self._filter_io_map[name] = {
                    "inputs": inputs,
                    "outputs": outputs,
                    "is_complex": is_complex
                }

                # Safe flag mapping: check if the character exists before comparing
                filters.append({
                    "name": name,
                    "descr": descr.strip(),
                    "is_dynamic": "N" in io_str,
                    "is_complex": is_complex,
                    "inputs": inputs,
                    "outputs": outputs,
                    "flags": {
                        "timeline": flags_raw[0] == 'T',
                        "slice_threading": flags_raw[1] == 'S',
                        # Only set True if the 3rd char exists AND is 'C'
                        "command_support": flags_raw[2] == 'C' if len(flags_raw) > 2 else False
                    }
                })
        return filters

    def parse_details(self, item_name):
        self._current_filter_name = item_name
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
        output = self._run_cmd(["-h", f"encoder={item_name}"])
        if "Unknown" in output or not output.strip():
            output = self._run_cmd(["-h", f"decoder={item_name}"])

        if not output or "Unknown" in output:
            return {"parameters": []}

        data = self._parse_av_options(output)

        # --- Inject missing x26x options from JSON ---
        try:
            json_path = os.path.join("codecs", "x26x_missing_parm_opts.json")
            if os.path.exists(json_path):
                with open(json_path, 'r', encoding='utf-8') as f:
                    missing_data = json.load(f)
                
                if item_name in missing_data:
                    overrides = missing_data[item_name]
                    for param in data.get("parameters", []):
                        p_name = param["name"]
                        if p_name in overrides:
                            for choice in overrides[p_name]:
                                # Append if choice is not already present
                                if not any(opt["name"] == choice for opt in param["options"]):
                                    param["options"].append({
                                        "name": choice,
                                        "value": choice,
                                        "descr": "Injected choice",
                                        "context": param["context"]
                                    })
        except Exception as e:
            # Optionally log: print(f"Error loading missing options: {e}")
            pass

        return data

class FFmpegFormatParser(FFmpegBaseParser):
    def parse_list(self):
        output = self._run_cmd(["-formats"])
        formats_map = {}
        pattern = re.compile(r"^\s([D\s])([E\s])\s+([\w,]+)\s+(.*)$")

        for line in output.splitlines():
            match = pattern.match(line)
            if match:
                can_demux, can_mux, name_str, descr = match.groups()
                names = name_str.split(',')
                primary_id = names[0]
                if primary_id not in formats_map:
                    formats_map[primary_id] = {"name": primary_id, "aliases": names[1:], "descr": descr.strip(), "is_demuxer": can_demux == 'D', "is_muxer": can_mux == 'E'}
                else:
                    formats_map[primary_id]["is_demuxer"] |= (can_demux == 'D')
                    formats_map[primary_id]["is_muxer"] |= (can_mux == 'E')
        return list(formats_map.values())

    def parse_details(self, item_name):
        final = {"name": item_name, "parameters": [], "extensions": []}
        
        # 1. Capture and Parse Muxer Help
        mux_out = self._run_cmd(["-h", f"muxer={item_name}"])
        # 2. Capture and Parse Demuxer Help
        demux_out = self._run_cmd(["-h", f"demuxer={item_name}"])
        
        # Extract extensions (usually same in both, but check both)
        for out in [mux_out, demux_out]:
            ext_match = re.search(r"Common extensions: (.*?)\.", out)
            if ext_match:
                exts = [e.strip() for e in ext_match.group(1).split(',')]
                for e in exts:
                    if e not in final["extensions"]:
                        final["extensions"].append(e)

        # 3. Parse and Merge Parameters
        mux_res = self._parse_av_options(mux_out)
        demux_res = self._parse_av_options(demux_out)
        
        # Use a dict to de-duplicate parameters by name while merging options
        merged_params = {}

        for p in mux_res["parameters"] + demux_res["parameters"]:
            p_name = p["name"]
            if p_name not in merged_params:
                merged_params[p_name] = p
            else:
                # Merge options if this parameter exists in both (e.g. 'protocol_whitelist')
                existing_options = {o["name"] for o in merged_params[p_name]["options"]}
                for new_opt in p["options"]:
                    if new_opt["name"] not in existing_options:
                        merged_params[p_name]["options"].append(new_opt)
                
                # Update context flags (Muxer might add 'E', Demuxer 'D')
                for flag, val in p["context"].items():
                    if val: merged_params[p_name]["context"][flag] = True

        final["parameters"] = list(merged_params.values())
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
            if os.name != 'nt':
                flags = 0x08000000 # CREATE_NO_WINDOW
            result = subprocess.run(cmd, capture_output=True, text=True, creationflags=flags, check=True)
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
