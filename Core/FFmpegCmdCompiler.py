from Models.TemplateDataModel import TemplateDataModel
from pathlib import Path
import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

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
        # We need to check if any stream belonging to a file is in 'copy' mode
        for f_idx, f_path in enumerate(src_files):
            # Check if all active streams for THIS file use 'copy'
            file_streams = [s for s in active_streams if s.get('file') == f_idx]
            
            # If all active streams for this specific file are 'copy', 
            # we can use fast input seeking for the whole file.
            if file_streams and all(FFmpegCmdCompiler._is_copy_stream(s) for s in file_streams):
                # Note: This assumes all streams in the file share the same trim.
                # If they differ, we take the first one found.
                first_s = file_streams[0]
                ss = first_s.get('trim_start')
                t = first_s.get('trim_length')
                
                if ss: cmd_parts.extend(["-ss", ss])
                if t:  cmd_parts.extend(["-t", t])

            cmd_parts.extend(["-i", str(f_path)])

        # --- PHASE 2: MAPPING AND OUTPUT OPTIONS ---
        type_counters = {"video": 0, "audio": 0, "subtitle": 0}
        output_cfg = job.get('output', {})
        container_short_name = output_cfg.get('container', 'auto')

        for stream in active_streams:
            template_data = FFmpegCmdCompiler._resolve_template(stream)
            s_type = FFmpegCmdCompiler._determine_type(stream, template_data)
            t_char = FFmpegCmdCompiler.TYPE_MAP.get(s_type, 'v')
            
            file_idx = stream.get('file', 0)
            src_idx = stream.get('index', 0)
            
            out_idx = type_counters.get(s_type, 0)
            specifier = f":{t_char}:{out_idx}"
            
            # Map the stream
            cmd_parts.extend(["-map", f"{file_idx}:{src_idx}"])

            # TRIM LOGIC: If NOT copy, put trim parameters AFTER map
            if not FFmpegCmdCompiler._is_copy_stream(stream):
                ss = stream.get('trim_start')
                t = stream.get('trim_length')
                if ss: cmd_parts.extend([f"-ss{specifier}", ss])
                if t:  cmd_parts.extend([f"-t{specifier}", t])

            # Apply Template Codecs/Params
            if template_data:
                codec = template_data.get('codec', 'copy')
                cmd_parts.extend([f"-c{specifier}", codec])

                params = template_data.get('parameters', {}).get('options', {})
                for key, val in params.items():
                    if key in FFmpegCmdCompiler.GLOBAL_OPTIONS:
                        cmd_parts.extend([f"-{key}", str(val)])
                    else:
                        cmd_parts.extend([f"-{key}{specifier}", str(val)])

                # Filters
                filter_data = template_data.get('filters', {})
                if filter_data.get('mode') == 'simple':
                    f_str = FFmpegCmdCompiler._build_simple_filter_string(filter_data.get('entries', []))
                    if f_str:
                        cmd_parts.extend([f"-{t_char}f{specifier}", f_str])

            FFmpegCmdCompiler._apply_disposition_deltas(container_short_name, cmd_parts, specifier, stream)
            type_counters[s_type] = out_idx + 1

        cmd_parts += ["-progress", "pipe:1"] #Add progress to stdout redirection

        # Setup Output Metadata
        out_dir = output_cfg.get('directory', '.')
        out_filename = (output_cfg.get('filename') or "").strip()

        # Determine Source Path for naming
        # Safely get the first file from 'src_files'
        source_path = None
        if src_files and len(src_files) > 0:
            source_path = Path(src_files[0])

        # Final Path Generation
        if container_short_name == "auto":
            if not out_filename and source_path:
                # Use original filename and extension
                final_output_path = Path(out_dir) / source_path.name
            else:
                # Fallback: custom name or source stem, otherwise 'output'
                name_to_use = out_filename or (source_path.stem if source_path else "output")
                # Original extension or .mkv
                ext = source_path.suffix if source_path else ".mkv"
                final_output_path = Path(out_dir) / f"{name_to_use}{ext}"
        else:
            # Explicit Container Selection
            name_to_use = out_filename or (source_path.stem if source_path else "output")
            
            from gi.repository import Gtk
            app = Gtk.Application.get_default()
            all_formats = getattr(app, 'ffmpeg_data', {}).get('formats', [])
            fmt_obj = next((f for f in all_formats if f['name'] == container_short_name), None)
            
            ext_suffix = output_cfg.get('container', "mkv")
            if fmt_obj and fmt_obj.get('extensions'):
                ext_suffix = fmt_obj['extensions'][0]
            
            final_output_path = Path(out_dir) / f"{name_to_use}.{ext_suffix}"

        # Output container format options
        out_container_params = output_cfg.get('container_parameters', [])
        for parm in out_container_params:
            key = parm.get('name')
            val = parm.get('value')
            
            if key and val is not None:
                cmd_parts.append(f"-{key}")
                if isinstance(val, list):
                    cmd_parts.append("+".join(map(str, val)) if key == "movflags" else ",".join(map(str, val)))
                else:
                    cmd_parts.append(str(val))

        # 5. Add final path
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
        """Helper to check if a stream is set to copy mode."""
        template_val = stream.get('template')
        if not template_val:
            return True # Default is copy
        
        # If it's a string, we need to look it up
        if isinstance(template_val, str):
            app = Gtk.Application.get_default()
            template_data = TemplateDataModel.get_template_by_name(app, template_val)
            if template_data:
                return template_data.get('codec') == 'copy'
        elif isinstance(template_val, dict):
            return template_val.get('codec') == 'copy'
        
        return True

    @staticmethod
    def _resolve_template(stream):
        template_val = stream.get('template')
        if isinstance(template_val, str):
            app = Gtk.Application.get_default()
            return TemplateDataModel.get_template_by_name(app, template_val)
        return template_val