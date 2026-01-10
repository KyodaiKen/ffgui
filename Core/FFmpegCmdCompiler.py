from Models.TemplateDataModel import TemplateDataModel
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

        # 1. Inputs
        for input_file in job.get('inputs', []):
            cmd_parts.append(f'-i "{input_file}"')

        # 2. Setup Counters
        type_counters = {"video": 0, "audio": 0, "subtitle": 0}
        active_streams = [s for s in job.get('streams', []) if s.get('active')]
        filter_complex_parts = []
        
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
            cmd_parts.append(f"-map {file_idx}:{src_idx}")

            if template_data:
                # Codec
                codec = template_data.get('codec', 'copy')
                cmd_parts.append(f"-c{specifier} {codec}")

                # Parameters
                params = template_data.get('parameters', {}).get('options', {})
                for key, val in params.items():
                    if key in FFmpegCmdCompiler.GLOBAL_OPTIONS:
                        cmd_parts.append(f"-{key} {val}")
                    else:
                        cmd_parts.append(f"-{key}{specifier} {val}")

                # Filters
                filter_data = template_data.get('filters', {})
                if filter_data.get('mode') == 'simple':
                    f_str = FFmpegCmdCompiler._build_simple_filter_string(filter_data.get('entries', []))
                    if f_str:
                        cmd_parts.append(f"-{t_char}f{specifier} \"{f_str}\"")

            # E. Increment Counter for this type
            type_counters[s_type] += 1

        return cmd_parts

    @staticmethod
    def _build_simple_filter_string(entries):
        res = []
        for e in entries:
            name = e.get('name')
            p = ":".join([f"{k}={v}" for k, v in e.get('params', {}).items()])
            res.append(f"{name}={p}" if p else name)
        return ",".join(res)