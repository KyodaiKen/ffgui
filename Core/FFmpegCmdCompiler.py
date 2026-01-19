from pathlib import Path
import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk
from Core.Utils import time_to_seconds
from Models.TemplateDataModel import TemplateDataModel

class FFmpegCmdCompiler:
    GLOBAL_OPTIONS = {'y', 'n', 'stats', 'loglevel', 'threads', 'f', 't', 'to', 'ss', 're', 'discard', 'benchmark'}
    
    TYPE_MAP = {
        "video": "v",
        "audio": "a",
        "subtitle": "s",
        "data": "d",
        "attachment": "t"
    }

    @staticmethod
    def gen_cmd_from_job(job):
        cmd_parts = ["-y"]
        src_files = job.get('sources', {}).get('files', [])
        streams = job.get('sources', {}).get('streams', [])
        active_streams = [s for s in streams if s.get('active')]

        if not src_files:
            return []

        # --- PHASE 1: INPUTS ---
        for f_idx, f_path in enumerate(src_files):
            file_streams = [s for s in active_streams if s.get('file') == f_idx]
            
            # Fast-seeking logic: If all streams for this file are 'copy', 
            # apply seeking before the input for maximum speed.
            if file_streams and all(FFmpegCmdCompiler._is_copy_stream(s) for s in file_streams):
                first_s = file_streams[0]
                ss = first_s.get('trim_start')
                t = first_s.get('trim_length')
                if ss: cmd_parts.extend(["-ss", str(time_to_seconds(ss))])
                if t:  cmd_parts.extend(["-t", str(time_to_seconds(t))])

            cmd_parts.extend(["-i", str(f_path)])

        # --- PHASE 2: MAPPING AND OUTPUT OPTIONS ---
        type_counters = {"video": 0, "audio": 0, "subtitle": 0}
        output_cfg = job.get('output', {})
        container_short_name = output_cfg.get('container', 'auto')

        for stream in active_streams:
            # 1. Resolve configuration (Template file OR Custom Row Settings)
            template_data = FFmpegCmdCompiler._resolve_template(stream)
            s_type = FFmpegCmdCompiler._determine_type(stream, template_data)
            t_char = FFmpegCmdCompiler.TYPE_MAP.get(s_type, 'v')
            
            file_idx = stream.get('file', 0)
            src_idx = stream.get('index', 0)
            
            # Calculate output specifier (e.g., :v:0)
            out_idx = type_counters.get(s_type, 0)
            specifier = f":{t_char}:{out_idx}"
            
            # 2. Map the stream
            cmd_parts.extend(["-map", f"{file_idx}:{src_idx}"])

            # 3. Metadata & Language (from SourceStreamRow entries)
            lang = stream.get('language')
            if lang:
                cmd_parts.extend([f"-metadata:s{specifier}", f"language={lang}"])
            
            metadata = stream.get('metadata', {})
            for key, val in metadata.items():
                if val:
                    cmd_parts.extend([f"-metadata:s{specifier}", f"{key}={val}"])

            # 4. Stream Delay (Offset)
            delay_ms = stream.get('stream_delay', "0")
            try:
                if float(delay_ms or 0) != 0:
                    cmd_parts.extend([f"-output_ts_offset{specifier}", f"{float(delay_ms)/1000.0}"])
            except (ValueError, TypeError):
                pass

            # 5. Trim Logic (If NOT using fast-seek copy mode)
            if not FFmpegCmdCompiler._is_copy_stream(stream):
                ss = stream.get('trim_start')
                t = stream.get('trim_length')
                if ss: cmd_parts.extend([f"-ss{specifier}", str(time_to_seconds(ss))])
                if t:  cmd_parts.extend([f"-t{specifier}", str(time_to_seconds(t))])

            # 6. Codecs and Parameters
            codec = template_data.get('codec', 'copy')
            cmd_parts.extend([f"-c{specifier}", codec])

            params = template_data.get('parameters', {}).get('options', {})
            for key, val in params.items():
                # Making sure booleans are processed correctly for FFMPEG
                if str(val).lower() in ["true", "false"]:
                    val = 1 if val == "true" else 0

                if key in FFmpegCmdCompiler.GLOBAL_OPTIONS:
                    cmd_parts.extend([f"-{key}", str(val)])
                else:
                    cmd_parts.extend([f"-{key}{specifier}", str(val)])

            # 7. Filters
            filter_data = template_data.get('filters', {})
            if filter_data.get('mode') == 'simple':
                f_str = FFmpegCmdCompiler._build_simple_filter_string(filter_data.get('entries', []))
                if f_str:
                    # FFmpeg uses -vf, -af, -sf but also -filter:v:0
                    cmd_parts.extend([f"-filter{specifier}", f_str])

            # 8. Dispositions
            FFmpegCmdCompiler._apply_disposition_deltas(container_short_name, cmd_parts, specifier, stream)
            
            # Increment counter for this type
            type_counters[s_type] = out_idx + 1

        # --- PHASE 3: OUTPUT FILE ---
        cmd_parts += ["-progress", "pipe:1"] 

        out_dir = output_cfg.get('directory', '.')
        out_filename = (output_cfg.get('filename') or "").strip()
        source_path = Path(src_files[0]) if src_files else None

        # Container / Extension Resolution
        if container_short_name == "auto":
            name_to_use = out_filename or (source_path.stem if source_path else "output")
            ext = source_path.suffix if source_path else ".mkv"
            final_output_path = Path(out_dir) / f"{name_to_use}{ext}"
        else:
            name_to_use = out_filename or (source_path.stem if source_path else "output")
            # Lookup extension from format data
            app = Gtk.Application.get_default()
            all_formats = getattr(app, 'ffmpeg_data', {}).get('formats', [])
            fmt_obj = next((f for f in all_formats if f['name'] == container_short_name), None)
            ext_suffix = fmt_obj['extensions'][0] if fmt_obj and fmt_obj.get('extensions') else container_short_name
            final_output_path = Path(out_dir) / f"{name_to_use}.{ext_suffix}"

        # Container parameters (e.g., movflags)
        out_container_params = output_cfg.get('container_parameters', [])
        for parm in out_container_params:
            key, val = parm.get('name'), parm.get('value')
            if key and val is not None:
                cmd_parts.append(f"-{key}")
                if isinstance(val, list):
                    cmd_parts.append("+".join(map(str, val)) if key == "movflags" else ",".join(map(str, val)))
                else:
                    cmd_parts.append(str(val))

        cmd_parts.append(str(final_output_path.resolve()))
        return cmd_parts

    @staticmethod
    def _build_simple_filter_string(entries):
        res = []
        for e in entries:
            name = e.get('name')
            p = ":".join([f"{k}={v}" for k, v in e.get('params', {}).items()])
            res.append(f"{name}={p}" if p else name)
        return ",".join(res)
    
    @staticmethod
    def _apply_disposition_deltas(container_short_name, cmd_parts, stream_specifier, stream_data):
        requested = stream_data.get('disposition', [])
        
        if isinstance(requested, str):
            requested = [v.strip() for v in requested.split(',') if v.strip()]
        elif not isinstance(requested, list):
            requested = []

        if requested:
            combined_flags = "+".join(requested)
            cmd_parts.append(f"-disposition{stream_specifier}")
            cmd_parts.append(combined_flags)

            # Map to titles for Matroska because the muxer ignores certain bits
            if container_short_name in ["matroska", "auto"] or "matroska" in str(container_short_name).lower():
                title_tag = ", ".join(requested).replace('_', ' ').title()
                cmd_parts.append(f"-metadata:s{stream_specifier}")
                cmd_parts.append(f"title={title_tag}")
        else:
            cmd_parts.append(f"-disposition{stream_specifier}")
            cmd_parts.append("0")

    def _determine_type(stream, template_data):
        """Determines the stream type, prioritizing template over stream metadata."""
        if template_data and template_data.get('type'):
            return template_data.get('type').lower()
        if stream.get('type'):
            return stream.get('type').lower()
        return "video" # Fallback

    @staticmethod
    def _is_copy_stream(stream):
        """Checks the resolved codec to see if it's 'copy'."""
        resolved = FFmpegCmdCompiler._resolve_template(stream)
        return resolved.get('codec') == 'copy'

    @staticmethod
    def _resolve_template(stream):
        """
        Loads a template. Prioritizes ephemeral 'settings' and 'filters' 
        stored in the stream object over the named template file.
        """
        transcoding_settings = stream.get('transcoding_settings', {})
        
        # 1. If we have settings or a codec explicitly defined in this stream
        if transcoding_settings.get('parameters') or transcoding_settings.get('codec'):
            return {
                "type": stream.get('type', 'video'),
                "codec": transcoding_settings.get('codec', 'copy'),
                # Standardize to the 'options' wrapper the compiler expects
                "parameters": {"options": transcoding_settings.get('parameters', {})},
                "filters": transcoding_settings.get('filters', {"mode": "simple", "entries": []})
            }

        # 2. Fallback to named template lookup
        template_name = stream.get('template')
        if isinstance(template_name, str) and template_name not in ["", "Manual / Custom Settings"]:
            app = Gtk.Application.get_default()
            # Standalone test script safety:
            if app:
                tpl = TemplateDataModel.get_template_by_name(app, template_name)
                if tpl: return tpl
        
        # 3. Last resort: Default Copy
        return {"codec": "copy", "type": stream.get('type', 'video')}