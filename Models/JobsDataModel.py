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
                "container": "mkv"
            }
        }

    @staticmethod
    def validate_job_data(app, job_data):
        """
        Checks if the job structure is sound and if referenced templates exist.
        Returns (is_valid, list_of_errors)
        """
        errors = []
        
        # 1. Check file indices
        num_files = len(job_data.get("sources", {}).get("files", []))
        streams = job_data.get("sources", {}).get("streams", [])
        
        # 2. Check template references
        available_templates = [t['name'] for t in TemplateDataModel.get_all_templates(app)]
        
        streams = job_data.get("sources", {}).get("streams", [])
        for i, stream in enumerate(streams):
            # Only validate template if the stream is ENABLED
            if stream.get("active", False):
                tpl_name = stream.get("template")
                if not tpl_name:
                    errors.append(f"Stream {i}: Active stream must have a template assigned.")
                elif tpl_name not in available_templates:
                    errors.append(f"Stream {i}: Referenced template '{tpl_name}' not found.")
                
        return len(errors) == 0, errors

    @staticmethod
    def load_from_file(file_path):
        path = pathlib.Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Job file not found: {file_path}")

        try:
            with open(path, 'r') as f:
                data = yaml.safe_load(f)
            
            if not data:
                return [] if isinstance(data, list) else JobsDataModel.create_empty_job()
            
            # If it's a list, sanitize every item inside it
            if isinstance(data, list):
                return [JobsDataModel.sanitize_job(item) for item in data]
            
            return JobsDataModel.sanitize_job(data)

        except Exception as e:
            print(f"Error loading job file: {e}")
            raise e

    @staticmethod
    def sanitize_job(data):
        """Helper to ensure a job dict has all required keys."""
        defaults = JobsDataModel.create_empty_job()
        if not data: return defaults
        
        # Deep merge logic
        for key in ["sources", "output"]:
            if key in data:
                # Merge sub-dictionaries
                temp = defaults[key].copy()
                temp.update(data[key])
                data[key] = temp
        
        # Merge top level
        defaults.update(data)
        return defaults

    @staticmethod
    def save_to_file(file_path, data):
        """Saves a single job OR a list of jobs to a YAML file."""
        path = pathlib.Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(path, 'w') as f:
                # The model now handles the YAML dumping logic for both types
                yaml.dump(data, f, sort_keys=False, indent=4)
            return True
        except Exception as e:
            print(f"Error saving file: {e}")
            raise e