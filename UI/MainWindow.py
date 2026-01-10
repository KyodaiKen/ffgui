import gi
import os
import threading
import time
from Models.JobsDataModel import JobsDataModel
gi.require_version("Gdk", "4.0")
from gi.repository import Gtk, Gio, Gdk, GLib
from UI.SettingsWindow import SettingsWindow
from UI.JobRow import JobRow
from UI.JobSetupWindow import JobSetupWindow
from UI.TemplateManagerWindow import TemplateManagerWindow
from UI.Constants import MENU_XML

class MainWindow(Gtk.ApplicationWindow):
    def __init__(self, **kargs):
        super().__init__(**kargs, title="ffGUI")
        self.app = Gtk.Application.get_default()
        self.set_size_request(640,480)

        header_bar = Gtk.HeaderBar()
        self.set_titlebar(header_bar)

        builder = Gtk.Builder.new_from_string(MENU_XML, -1)
        main_menu_mdl = builder.get_object("app-menu")

        menu_button = Gtk.MenuButton(icon_name="open-menu-symbolic", menu_model=main_menu_mdl)
        header_bar.pack_end(menu_button)

        # Main box of our window
        box_outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, vexpand=True, spacing=2)
        box_outer.props.margin_start = 6
        box_outer.props.margin_end = 6
        box_outer.props.margin_top = 6
        box_outer.props.margin_bottom = 6
        self.set_child(box_outer)

        # Register main menu actions
        actions = [
            ("open_joblist", self.on_open_joblist),
            ("save_joblist", self.on_save_joblist),
            ("clear_joblist", self.on_clear_joblist),
            ("create_job", self.on_create_job),
            ("create_jobs_from_dir", self.on_create_jobs_from_dir),
            ("pref", self.on_pref),
            ("tplm", self.on_tplm),
            ("about", self.on_about),
            ("quit", self.on_quit)
        ]

        for name, callback in actions:
            action = Gio.SimpleAction.new(name, None)
            action.connect("activate", callback)
            self.add_action(action)

        # List box with ScrolledWindow
        self.scrolled_window = Gtk.ScrolledWindow(vexpand=True)
        self.scrolled_window.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)

        self.listbox = Gtk.ListBox()
        self.listbox.set_selection_mode(Gtk.SelectionMode.MULTIPLE)
        self.listbox.set_activate_on_single_click(False)
        
        self.scrolled_window.set_child(self.listbox)
        box_outer.append(self.scrolled_window)

        self.drag_gesture = Gtk.GestureDrag.new()
        self.drag_gesture.set_propagation_phase(Gtk.PropagationPhase.BUBBLE)
        #self.drag_gesture.connect("drag-begin", self.on_drag_begin)
        self.drag_gesture.connect("drag-update", self.on_drag_update)
        #self.drag_gesture.connect("drag-end", self.on_drag_end)
        self.listbox.add_controller(self.drag_gesture)
    
        #builder = Gtk.Builder.new_from_string(self.CONTEXT_MENU_XML, -1)
        #self.context_menu_model = builder.get_object("context-menu")

        # Inner bottom box for bottom controls
        box_bottom = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        box_bottom.props.margin_start = 2
        box_bottom.props.margin_end = 2
        box_bottom.props.margin_top = 2
        box_bottom.props.margin_bottom = 2
        box_outer.append(box_bottom)

        bottom_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        label = Gtk.Label()
        label.set_markup("<big>Total</big>")
        pb = Gtk.ProgressBar(hexpand=True)
        pb.set_text("34.38%, ETA 8s")
        pb.set_show_text(True)
        pb.set_fraction(0.34375)
        btn_start = Gtk.Button(label="Start")
        bottom_box.append(label)
        bottom_box.append(pb)
        bottom_box.append(btn_start)
        box_bottom.append(bottom_box)

        # Drop Target Setup
        # We look for Gdk.FileList (Standard for dragging files from file manager)
        drop_target = Gtk.DropTarget.new(Gdk.FileList, Gdk.DragAction.COPY)
        drop_target.connect("drop", self.on_file_drop)
        self.listbox.add_controller(drop_target)

    #def on_drag_begin(self, gesture, start_x, start_y):
    #    pass

    def on_drag_update(self, gesture, offset_x, offset_y):
        success, _, start_y = gesture.get_start_point()
        if not success: return

        # Modifier check for selection logic
        state = gesture.get_current_event_state()
        is_ctrl = state & Gdk.ModifierType.CONTROL_MASK

        rect_y = start_y if offset_y > 0 else start_y + offset_y
        height = abs(offset_y)
        top, bottom = rect_y, rect_y + height
        row = self.listbox.get_first_child()
        while row:
            if isinstance(row, Gtk.ListBoxRow):
                success, rect = row.compute_bounds(self.listbox)
                if success:
                    row_y = rect.get_y()
                    row_h = rect.get_height()
                    row_bottom = row_y + row_h

                    if row_bottom >= top and row_y <= bottom:
                        self.listbox.select_row(row)
                    elif not is_ctrl:
                        self.listbox.unselect_row(row)
            row = row.get_next_sibling()

    #def on_drag_end(self, gesture, start_x, start_y):
    #    pass

    # Main menu events
    def on_open_joblist(self, action, param):
        dialog = Gtk.FileDialog.new()
        dialog.set_title("Open Job List")
        
        # Filtering for YAML
        filters = Gio.ListStore.new(Gtk.FileFilter)
        yaml_filter = Gtk.FileFilter()
        yaml_filter.set_name("YAML Job Lists")
        yaml_filter.add_pattern("*.yaml")
        filters.append(yaml_filter)
        dialog.set_filters(filters)

        dialog.open(self, None, self._on_open_joblist_finish)

    def _on_open_joblist_finish(self, dialog, result):
        try:
            file = dialog.open_finish(result)
            if file:
                # USE THE MODEL
                data = JobsDataModel.load_from_file(file.get_path())

                # If the model returned a list, populate the UI
                if isinstance(data, list):
                    self.on_clear_joblist(None, None)
                    for job_dict in data:
                        self.add_job_to_list(job_dict)
                else:
                    # If it was a single job file, just add it to current list
                    self.add_job_to_list(data)
        except Exception as e:
            self._show_error("Load Error", str(e))

    def on_save_joblist(self, action, param):
        # 1. Gather all job data from the rows
        all_jobs = []
        child = self.listbox.get_first_child()
        while child:
            if isinstance(child, JobRow):
                all_jobs.append(child.job_data)
            child = child.get_next_sibling()

        if not all_jobs:
            return

        # 2. Open Save Dialog
        dialog = Gtk.FileDialog.new()
        dialog.set_title("Save Job List")
        dialog.set_initial_name("my_jobs.yaml")
        
        dialog.save(self, None, self._on_save_joblist_finish, all_jobs)
    
    def _on_save_joblist_finish(self, dialog, result, all_jobs):
        try:
            file = dialog.save_finish(result)
            if file:
                # USE THE MODEL
                JobsDataModel.save_to_file(file.get_path(), all_jobs)
        except Exception as e:
            self._show_error("Save Error", str(e))

    def _show_error(self, title, msg):
        alert = Gtk.AlertDialog(message=title, detail=msg)
        alert.show(self)

    def on_clear_joblist(self, action, param):
        """Removes all rows from the listbox after user confirmation."""
        # Check if there is anything to clear
        if self.get_total_jobs() == 0:
            return

        # Create a non-blocking alert dialog
        alert = Gtk.AlertDialog(
            message="Clear Job List?",
            detail="This will remove all jobs from the current session. This action cannot be undone.",
            buttons=["Cancel", "Clear All"]
        )
        
        # In GTK4, choose() is preferred over the old run() 
        # result is the index of the button clicked (0 for Cancel, 1 for Clear All)
        alert.choose(self, None, self._on_clear_confirmed)

    def _on_clear_confirmed(self, alert, result):
        if result == 1:
            # result 1 corresponds to "Clear All" button index
            self.listbox.remove_all()
            print("Job list cleared.")

    def on_create_job(self, action, param):
        # We pass "create" mode. The JobSetupWindow will use JobsDataModel.create_empty_job()
        wnd = JobSetupWindow(
            parent_window=self, 
            mode="create"
        )
        # We define a callback so the setup window can "return" the job data
        wnd.on_job_setup_finished = self.add_job_to_list
        wnd.present()

    def add_job_to_list(self, job_dict):
        """Callback used by JobSetupWindow to add a finished job structure to the UI"""
        # Generate an ID based on current list length
        job_id = self.get_total_jobs()
        job_row = JobRow(job_id, job_dict, None, self.app)
        self.listbox.append(job_row)

    def get_total_jobs(self):
        count = 0
        child = self.listbox.get_first_child()
        while child:
            if isinstance(child, Gtk.ListBoxRow):
                count += 1
            child = child.get_next_sibling()
        return count

    def on_create_jobs_from_dir(self, action, param):
        dialog = Gtk.FileDialog.new()
        dialog.set_title("Select Directory of Media Files")
        dialog.select_folder(self, None, self._on_dir_import_finish)

    def on_file_drop(self, target, value, x, y):
        files = value.get_files()
        paths = [f.get_path() for f in files]
        
        all_paths = []
        for p in paths:
            if os.path.isdir(p):
                # Expand folder content
                for entry in os.scandir(p):
                    if entry.is_file():
                        all_paths.append(entry.path)
            else:
                all_paths.append(p)

        self._process_files_to_jobs(all_paths)
        return True

    def _on_dir_import_finish(self, dialog, result):
        folder = dialog.select_folder_finish(result)
        if not folder: return
        
        path = folder.get_path()
        all_files = [os.path.join(path, f) for f in os.listdir(path)]
        self._process_files_to_jobs(all_files)

    def _process_files_to_jobs(self, file_paths):
        """Universal threaded processor. Accepts all files; let FFMPEG decide validity."""
        if not file_paths: return

        progress_win = Gtk.Window(title="Importing Media...", transient_for=self, modal=True)
        progress_win.set_default_size(300, 100)
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10, margin_start=20, margin_end=20, margin_top=20, margin_bottom=20)
        lbl = Gtk.Label(label="Probing files...")
        pbar = Gtk.ProgressBar(show_text=True)
        vbox.append(lbl)
        vbox.append(pbar)
        progress_win.set_child(vbox)

        start_time = time.time()

        def worker():
            # Remove directory checks here - we only want files for the probe
            files_to_probe = [p for p in file_paths if os.path.isfile(p)]
            total = len(files_to_probe)
            
            for i, file_path in enumerate(files_to_probe):
                # _get_job_data_from_file is called here in the background thread
                job_dict = self._get_job_data_from_file(file_path)
                
                def update_ui(j=job_dict, idx=i):
                    if j: 
                        self.add_job_to_list(j)
                    
                    pbar.set_fraction((idx + 1) / total)
                    pbar.set_text(f"{idx + 1} / {total}")
                    
                    # Show progress window only if processing takes > 1 second
                    if not progress_win.get_visible() and (time.time() - start_time) > 0.5:
                        progress_win.present()

                GLib.idle_add(update_ui)

            GLib.idle_add(progress_win.destroy)

        threading.Thread(target=worker, daemon=True).start()

    def _get_job_data_from_file(self, file_path):
        """Probes a file and returns a Job dictionary. Returns None if probe fails."""
        from Models.JobsDataModel import JobsDataModel
        from Core.Utils import get_file_title
        
        try:
            # If this fails, it's not a supported media file
            info = self.app.parsers['media'].get_info(file_path)
            if not info or "streams" not in info:
                return None

            job = JobsDataModel.create_empty_job()
            job["name"] = get_file_title(file_path)
            job["sources"]["files"] = [file_path]
            job["output"]["directory"] = os.path.dirname(file_path)
            job["output"]["filename"] = "" 
            job["output"]["container"] = "auto"
            
            for idx, stream in enumerate(info.get('streams', [])):
                stype = stream.get('codec_type', 'data').capitalize()
                job["sources"]["streams"].append({
                    "file": 0, "index": idx,
                    "active": stype.lower() in ['video', 'audio'],
                    "template": f"Copy {stype}",
                    "disposition": [],
                    "language": stream.get('tags', {}).get('language', '')
                })
            return job
        except Exception as e:
            print(f"FFMPEG could not probe {file_path}: {e}")
            return None

    def _create_job_from_single_file(self, file_path):
        """Generates a job with your specific defaults."""
        from Models.JobsDataModel import JobsDataModel
        from Core.Utils import get_file_title
        
        # 1. Create base structure
        job = JobsDataModel.create_empty_job()
        
        # 2. Set Names and Paths
        job["name"] = get_file_title(file_path)
        job["sources"]["files"] = [file_path]
        job["output"]["directory"] = os.path.dirname(file_path)
        job["output"]["filename"] = "" # Leave blank as requested
        job["output"]["container"] = "auto"
        
        # 3. Probe file to set stream templates
        try:
            info = self.app.parsers['media'].get_info(file_path)
            for idx, stream in enumerate(info.get('streams', [])):
                stype = stream.get('codec_type', 'data').capitalize()
                
                # Apply the "Copy <Type>" default
                template_name = f"Copy {stype}"
                
                job["sources"]["streams"].append({
                    "file": 0,
                    "index": idx,
                    "active": stype.lower() in ['video', 'audio'], # Default active V/A
                    "template": template_name,
                    "disposition": [],
                    "language": stream.get('tags', {}).get('language', '')
                })
        except Exception as e:
            print(f"Skipping {file_path} due to probe error: {e}")
            return

        # 4. Add to UI
        self.add_job_to_list(job)

    def on_pref(self, action, param):
        """Triggered by win.pref in the main menu."""
        # We pass self (MainWindow) as parent and self.app as the application instance
        settings_win = SettingsWindow(parent=self, app_instance=self.app)
        settings_win.present()

    def on_tplm(self, action, param):
        win = TemplateManagerWindow(parent_window=self)
        win.present()

    def on_about(self, action, param):
        about_dialog = Gtk.AboutDialog(transient_for=self, modal=True)
        about_dialog.present()

    def on_quit(self, action, param):
        if self.app:
            self.app.quit()