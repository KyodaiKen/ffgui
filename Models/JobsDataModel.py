import yaml
import pathlib
from Models.TemplateDataModel import TemplateDataModel

class JobsDataModel:
    @staticmethod
    def create_empty_job():
        """Returns a dictionary representing a fresh job structure."""
        return {
            "name": "New Job",
            "use_hwdec": False,
            "hwdec_device_id": 0,
            "sources": {
                "files": [],
                "streams": []
            },
            "output": {
                "directory": "",
                "filename": "",
                "container": "mkv",
                "container_parameters": []
            }
        }

    @staticmethod
    def validate_job_data(app, job_data):
        """
        Checks if the job structure is sound and if referenced templates exist.
        Updated to support the nested 'transcoding_settings' structure.
        """
        errors = []
        
        # 1. Check file existence
        files = job_data.get("sources", {}).get("files", [])
        if not files:
            errors.append("Job must have at least one source file.")
        
        # 2. Check stream configuration
        available_templates = [t['name'] for t in TemplateDataModel.get_all_templates(app)]
        
        streams = job_data.get("sources", {}).get("streams", [])
        for i, stream in enumerate(streams):
            if stream.get("active", False):
                tpl_name = stream.get("template")
                
                # Check the NESTED transcoding_settings
                trans = stream.get("transcoding_settings", {})
                
                if not tpl_name or tpl_name == "Manual / Custom Settings":
                    if not trans.get("codec"):
                        errors.append(f"Stream {i} has no codec defined.")
                else:
                    if tpl_name not in available_templates:
                        errors.append(f"Stream {i} references non-existent template: '{tpl_name}'")
        
        return len(errors) == 0, errors

    @staticmethod
    def normalize_job(data):
        defaults = JobsDataModel.create_empty_job()
        for key in ["sources", "output"]:
            if key not in data: data[key] = defaults[key].copy()

        streams = data["sources"].get("streams", [])
        for s in streams:
            # Migration logic for older flat files
            if "transcoding_settings" not in s:
                s["transcoding_settings"] = {
                    "codec": s.pop("codec", "copy"),
                    "parameters": s.pop("settings", {}),
                    "filters": s.pop("filters", {"mode": "simple", "entries": []})
                }
        return data

    @staticmethod
    def load_from_file(file_path):
        """Loads jobs from a YAML file and normalizes their structure."""
        with open(file_path, 'r') as f:
            data = yaml.safe_load(f)
        
        # If it's a list of jobs, normalize each one
        if isinstance(data, list):
            return [JobsDataModel.normalize_job(job) for job in data]
        # If it's a single job dict
        return JobsDataModel.normalize_job(data)

    @staticmethod
    def save_to_file(file_path, data):
        """Saves a single job OR a list of jobs to a YAML file."""
        path = pathlib.Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(path, 'w') as f:
                # Use sort_keys=False to keep the structure readable and maintain order
                yaml.dump(data, f, sort_keys=False, indent=4, default_flow_style=False)
            return True
        except Exception as e:
            print(f"Error saving file: {e}")
            raise e