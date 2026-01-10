import pathlib
import yaml
import os

class TemplateDataModel:
    import pathlib
import yaml

class TemplateDataModel:
    import pathlib
import yaml
import os

class TemplateDataModel:
    @staticmethod
    def get_all_templates(app):
        # 1. Define the Application Root (where the script is)
        # This is the "System" source
        app_root = pathlib.Path(__file__).parent.parent.resolve() 
        system_path = (app_root / "templates").resolve()
        
        # 2. Define the User Config path from the App object
        user_path = None
        if hasattr(app, 'templates_dir') and app.templates_dir:
            user_path = pathlib.Path(app.templates_dir).resolve()

        # 3. Collect unique paths to scan
        scan_locations = {system_path: "System"}
        if user_path and user_path != system_path:
            scan_locations[user_path] = "User"
            
        found = []
        for path_obj, origin_label in scan_locations.items():
            if path_obj.exists() and path_obj.is_dir():
                for file in path_obj.glob("*.yaml"):
                    try:
                        with open(file, 'r') as f:
                            data = yaml.safe_load(f)
                            if not data: continue
                            
                            # Double check: if it's inside the app root, it's System
                            # This handles the "Portable" edge case
                            is_inside_app = file.resolve().is_relative_to(app_root)
                            final_origin = "System" if is_inside_app else origin_label

                            found.append({
                                "name": file.stem, 
                                "path": str(file.resolve()),
                                "type": str(data.get("type", "unknown")).upper(),
                                "origin": final_origin,
                                "data": data,
                                "readonly": not os.access(file, os.W_OK)
                            })
                    except: continue
        
        return sorted(found, key=lambda x: (x['type'], x['name'].lower()))

    @staticmethod
    def get_templates_by_type(app, target_type):
        # Pass app down to the main scanner
        all_t = TemplateDataModel.get_all_templates(app)
        return [t for t in all_t if t['type'].lower() == target_type.lower()]

    @staticmethod
    def save_template(templates_dir, filename, yaml_data):
        base_dir = pathlib.Path(templates_dir).resolve()
        base_dir.mkdir(parents=True, exist_ok=True)
        
        clean_data = {k: v for k, v in yaml_data.items() if k != "name"}
        save_path = base_dir / f"{filename}.yaml"
        
        with open(save_path, 'w') as f:
            yaml.dump(clean_data, f, sort_keys=False, indent=4)
        return str(save_path.resolve())

    @staticmethod
    def rename_template(old_path_str, new_name):
        old_path = pathlib.Path(old_path_str)
        new_path = old_path.with_name(f"{new_name}.yaml")
        if new_path.exists():
            return False, "A file with this name already exists."
        try:
            os.rename(old_path, new_path)
            return True, str(new_path.resolve())
        except Exception as e:
            return False, str(e)

    @staticmethod
    def create_empty_template(stream_type="video"):
        """Returns structure containing only transcoding parameters."""
        return {
            "name": "New Template",
            "type": "video",
            "codec": "libx264",
            "parameters": {
                "options": {
                    "b": "6000k",
                    "preset": "medium"
                }
            },
            "filters": {
                "mode": "simple",
                "entries": []
            }
        }