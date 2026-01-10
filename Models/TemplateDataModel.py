import pathlib
import yaml
import os

class TemplateDataModel:
    @staticmethod
    def get_template_by_name(app, template_name):
        """
        Searches for a template by its filename (stem) and returns a flat 
        dictionary containing file metadata merged with YAML content.
        """
        app_root = pathlib.Path(__file__).parent.parent.resolve() 
        system_path = (app_root / "templates").resolve()
        
        scan_paths = [system_path]
        if hasattr(app, 'templates_dir') and app.templates_dir:
            scan_paths.append(pathlib.Path(app.templates_dir).resolve())

        # 1. Direct File Lookup (Optimized)
        for base_path in scan_paths:
            potential_file = base_path / f"{template_name}.yaml"
            if potential_file.exists():
                try:
                    with open(potential_file, 'r') as f:
                        yaml_content = yaml.safe_load(f)
                        if yaml_content:
                            # Create the flat structure
                            res = {
                                "name": potential_file.stem,
                                "path": str(potential_file.resolve()),
                                "origin": "System" if potential_file.is_relative_to(app_root) else "User"
                            }
                            # Merge YAML (type, codec, parameters, filters) into top level
                            res.update(yaml_content)
                            return res
                except Exception as e:
                    print(f"Error reading template {template_name}: {e}")
                    continue

        # 2. Fallback: Scan (Handles case-sensitivity or symlinks)
        all_templates = TemplateDataModel.get_all_templates(app)
        for t in all_templates:
            if t['name'] == template_name:
                # all_templates is already flat, return as-is
                return t

        return None

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

                            # Replace the old found.append with this:
                            template_entry = {
                                "name": file.stem, 
                                "path": str(file.resolve()),
                                "origin": final_origin,
                                "readonly": not os.access(file, os.W_OK)
                            }

                            # Merge the YAML content (data) directly into the entry
                            # This puts 'type', 'codec', 'parameters', and 'filters' at the top level
                            template_entry.update(data)

                            # Ensure 'type' is uppercase for the sorting logic in the model
                            template_entry["type"] = str(template_entry.get("type", "unknown")).upper()

                            found.append(template_entry)
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
            "parameters": {},
            "filters": {
                "mode": "simple",
                "entries": []
            }
        }