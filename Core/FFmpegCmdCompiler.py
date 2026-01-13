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

        # 1. Access files from the standardized 'sources' key
        src_files = job.get('sources', {}).get('files', [])

        print(job)
        
        if not src_files:
            print("CRITICAL: No source files found in job structure!")
            return []

        for f in src_files:
            cmd_parts.extend(["-i", f'{f}'])

        # 2. Setup Counters
        type_counters = {"video": 0, "audio": 0, "subtitle": 0}
        active_streams = [s for s in job.get('sources', {}).get('streams', []) if s.get('active')]

        # We already need the container format selection here for _apply_disposition_deltas
        # so it can map disposition for matroska correctly if the container matroska is requested:
        output_cfg = job.get('output', {})
        container_short_name = output_cfg.get('container', 'auto')

        for stream in active_streams:
            # A. Resolve Template First to find the true stream type
            template_val = stream.get('template')
            template_data = None
            
            if isinstance(template_val, str):
                from gi.repository import Gtk
                app = Gtk.Application.get_default()
                template_data = TemplateDataModel.get_template_by_name(app, template_val)
            elif isinstance(template_val, dict):
                template_data = template_val

            # B. Determine Type (Try template first, then stream, then default to video)
            s_type = "video"
            if template_data and template_data.get('type'):
                s_type = template_data.get('type').lower()
            elif stream.get('type'):
                s_type = stream.get('type').lower()

            t_char = FFmpegCmdCompiler.TYPE_MAP.get(s_type, 'v')
            
            # C. Mapping Indices
            file_idx = stream.get('file', 0)
            src_idx = stream.get('index', 0)
            
            if s_type not in type_counters:
                type_counters[s_type] = 0
            
            out_idx = type_counters[s_type]
            specifier = f":{t_char}:{out_idx}"
            
            # D. Compile Command Parts
            cmd_parts.append("-map")
            cmd_parts.append(f"{file_idx}:{src_idx}")

            if template_data:
                # Codec
                codec = template_data.get('codec', 'copy')
                cmd_parts.append(f"-c{specifier}")
                cmd_parts.append(f"{codec}")

                # Parameters
                params = template_data.get('parameters', {}).get('options', {})
                for key, val in params.items():
                    if key in FFmpegCmdCompiler.GLOBAL_OPTIONS:
                        cmd_parts.append(f"-{key}")
                        cmd_parts.append(f"{val}")
                    else:
                        cmd_parts.append(f"-{key}{specifier}")
                        cmd_parts.append(f"{val}")

                # Filters
                filter_data = template_data.get('filters', {})
                if filter_data.get('mode') == 'simple':
                    f_str = FFmpegCmdCompiler._build_simple_filter_string(filter_data.get('entries', []))
                    if f_str:
                        cmd_parts.append(f"-{t_char}f{specifier}")
                        cmd_parts.append(f"\"{f_str}\"")

            FFmpegCmdCompiler._apply_disposition_deltas(container_short_name, cmd_parts, specifier, stream)

            # E. Increment Counter for this type
            type_counters[s_type] += 1

        cmd_parts += ["-progress", "-"] #Add progress to stdout redirection

        # 2. Setup Output Metadata
        out_dir = output_cfg.get('directory', '.')
        out_filename = (output_cfg.get('filename') or "").strip()

        # 3. Determine Source Path for naming
        # Safely get the first file from 'src_files'
        source_path = None
        if src_files and len(src_files) > 0:
            source_path = Path(src_files[0])

        # 4. Final Path Generation
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