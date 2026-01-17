import gi

from UI.BatchOutputDirWindow import BatchOutputDirWindow
gi.require_version("Gdk", "4.0")
from gi.repository import Gtk, Gio, Gdk
from UI.JobSetupWindow import JobSetupWindow
from UI.TemplateManagerWindow import TemplateManagerWindow
from UI.Constants import CONTEXT_MENU_XML

class JobRow(Gtk.ListBoxRow):
    def __init__(self, job_id, job_data, _, app):
        super().__init__()
        self.job_id = job_id
        self.job_data = job_data
        self.app = app
        self.error_log = ""

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_child(vbox)

        # Header box to hold Label and the Status Icon
        header_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.label = Gtk.Label(xalign=0, hexpand=True)
        
        # The status icon (Checkmark/X)
        self.img_status = Gtk.Image()
        self.img_status.set_visible(False) # Hide by default
        
        header_hbox.append(self.label)
        header_hbox.append(self.img_status)
        vbox.append(header_hbox)

        self.lbl_info = Gtk.Label(xalign=0)

        self.progress_bar = Gtk.ProgressBar(hexpand=True)
        self.progress_bar.set_show_text(True)
        
        vbox.append(self.lbl_info)
        vbox.append(self.progress_bar)
        
        gesture = Gtk.GestureClick.new()
        gesture.set_button(3)
        gesture.connect("pressed", self.on_right_click)
        self.add_controller(gesture)

        self.setup_context_menu(_)
        self.update_job_data(job_data)

    def setup_context_menu(self, _):
        builder = Gtk.Builder.new_from_string(CONTEXT_MENU_XML, -1)
        menu_model = builder.get_object("context-menu")

        self.action_group = Gio.SimpleActionGroup.new()
        
        def add_act(name, callback, enabled=True):
            act = Gio.SimpleAction.new(name, None)
            act.connect("activate", callback)
            act.set_enabled(enabled)
            self.action_group.add_action(act)

        add_act("job_setup", self.on_job_setup)
        add_act("remove_job", self.on_remove)
        add_act("job_clone", self.on_clone)

        add_act("toggle_video", lambda a, p: self.on_smart_toggle("video"))
        add_act("toggle_audio", lambda a, p: self.on_smart_toggle("audio"))
        add_act("toggle_subtitles", lambda a, p: self.on_smart_toggle("subtitles"))

        # Error Log Action (Disabled by default)
        add_act("view_error", self.on_view_error, enabled=False)

        add_act("batch_tpl_video", lambda a, p: self.on_batch_template("video"))
        add_act("batch_tpl_audio", lambda a, p: self.on_batch_template("audio"))
        add_act("batch_tpl_subtitle", lambda a, p: self.on_batch_template("subtitles"))
        add_act("batch_chg_out_dir", self.on_batch_chg_output_dir)
        
        self.insert_action_group("context", self.action_group)

        self.popover = Gtk.PopoverMenu.new_from_model(menu_model)
        self.popover.set_parent(self)
        self.popover.set_has_arrow(False)
    
    def update_status(self, text):
        """Updates the progress bar text and fraction for this specific row"""
        # We can try to parse the percentage from the FFmpeg string 
        # (JobRunner usually sends "Percentage% Speed=... ETA=...")
        try:
            if "%" in text:
                pct_str = text.split("%")[0].strip()
                fraction = float(pct_str) / 100.0
                self.progress_bar.set_fraction(fraction)
        except:
            pass
            
        self.progress_bar.set_text(text)

    def update_job_data(self, new_data):
        """Updates the internal data and UI of this specific row"""
        self.job_data = new_data
        title = new_data.get("name") or "Job"
        self.label.set_markup(f"<b>{title}</b>")
        
        # Flexibly handle 'sources' or 'inputs'
        sources = new_data.get("sources") or new_data # Fallback if flat
        files = sources.get("files") or new_data.get("inputs") or []
        streams = sources.get("streams") or new_data.get("streams") or []
        
        src_count = len(files)
        strm_count = len(streams)
        self.lbl_info.set_text(f"{src_count} Files, {strm_count} Streams")

    def create_action(self, name, callback):
        action = Gio.SimpleAction.new(name, None)
        action.connect("activate", callback)
        return action

    def set_progress(self, fraction, text):
        self.progress_bar.set_fraction(fraction)
        self.progress_bar.set_text(text)

    def on_right_click(self, gesture, n_press, x, y):
        listbox = self.get_parent()
        
        # If the right-clicked row isn't selected, make it the only selection
        # If it is already selected, leave the multi-selection alone
        if not self.is_selected():
            listbox.select_row(self)

        rect = Gdk.Rectangle()
        rect.x, rect.y, rect.width, rect.height = x, y, 1, 1
        self.popover.set_pointing_to(rect)
        self.popover.popup()

    def get_selected_job_ids(self):
        """Helper to get IDs of all currently selected rows"""
        listbox = self.get_parent()
        selected_rows = listbox.get_selected_rows()
        return [row.job_id for row in selected_rows]
    
    def on_job_setup(self, action, param):
        """Opens Setup window in EDIT mode"""
        wnd = JobSetupWindow(
            parent_window=self.get_root(), 
            mode="edit", 
            job=self.job_data
        )
        # Update this specific row when finished
        wnd.on_job_setup_finished = self.update_job_data
        wnd.present()

    def on_remove(self, action, param):
        listbox = self.get_parent()
        selected_rows = listbox.get_selected_rows()
        
        if not selected_rows:
            return

        job_names = []
        for row in selected_rows:
            raw_text = row.label.get_text()
            job_names.append(f"• {raw_text}")

        message_list = "\n".join(job_names)
        count = len(selected_rows)

        alert = Gtk.AlertDialog(
            message=f"Remove {count} {'job' if count == 1 else 'jobs'}?",
            detail=f"The following jobs will be removed:\n\n{message_list}",
            buttons=["Cancel", "Remove"],
            default_button=1,
            cancel_button=0
        )
        root_window = self.get_root() 
        
        alert.choose(root_window, None, self.on_remove_confirmed, selected_rows)

    def on_remove_confirmed(self, alert, result, selected_rows):
        # result is the index of the button clicked (0 for Cancel, 1 for Remove)
        try:
            response = alert.choose_finish(result)
            if response == 1: # User clicked "Remove"
                listbox = self.get_parent()
                for row in selected_rows:
                    listbox.remove(row)
                print(f"Successfully removed {len(selected_rows)} items.")
        except Exception as e:
            print(f"Dialog error: {e}")

    def on_batch_template(self, target_type):
        """Opens the unified Manager in picker mode filtered by stream type"""
        self._current_batch_type = target_type 

        # Initialize in picker_mode
        picker = TemplateManagerWindow(
            parent_window=self.get_root(),
            picker_mode=True,           # New parameter
            stream_type=target_type,    # New parameter (replaces current_val logic)
            on_select=self._apply_batch_template_to_selected
        )
        picker.present()

    def _apply_batch_template_to_selected(self, template_name):
        """Applies a template to all relevant streams in ALL selected jobs without re-probing."""
        target_type = self._current_batch_type
        listbox = self.get_parent()
        selected_rows = [row for row in listbox.get_selected_rows() if isinstance(row, JobRow)]

        for row in selected_rows:
            streams = row.job_data["sources"]["streams"]
            
            for s_entry in streams:
                # We check the 'type' which was saved during the initial probe/import
                if s_entry.get("type") == target_type:
                    s_entry["template"] = template_name
            
            # Refresh UI (This is now instant)
            row.update_job_data(row.job_data)
        
    def on_clone(self, action, param):
        """Copies the job data and opens JobSetupWindow in clone mode"""
        import copy
        
        # Get the main window (root) so we can access its methods
        main_window = self.get_root()
        if not main_window:
            return

        # Deep copy the current row's data
        cloned_data = copy.deepcopy(self.job_data)
        
        # Open the setup window in clone mode
        wnd = JobSetupWindow(
            parent_window=main_window,
            mode="clone",
            job=cloned_data
        )
        
        # This is the crucial callback:
        # We tell the setup window to send the finished job back to MainWindow
        wnd.on_job_setup_finished = main_window.add_job_to_list
        wnd.present()

    def add_cloned_job_to_list(self, final_job_data):
        """Callback to insert the newly cloned job into the main UI"""
        # We access the main window's 'add_job' method through the app 
        # or by looking at the parent's structure.
        # Assuming your MainWindow has an 'add_job' method:
        main_window = self.get_root()
        if hasattr(main_window, "add_job"):
            main_window.add_job(final_job_data)

    def on_view_error(self, action, param):
        """Shows the error log in a scrollable window with monospace font."""
        log_window = Gtk.Window(
            title=f"Error Log: {self.job_data.get('name')}",
            transient_for=self.get_root(),
            modal=True,
            default_width=800,
            default_height=500
        )

        # Scrolled Window to allow navigation
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_margin_start(12)
        scrolled.set_margin_end(12)
        scrolled.set_margin_top(12)
        scrolled.set_margin_bottom(12)
        
        # TextView for the log content
        text_view = Gtk.TextView()
        text_view.set_name("ffmpeg_error_log")
        text_view.set_editable(False)
        text_view.set_cursor_visible(False)
        text_view.set_wrap_mode(Gtk.WrapMode.NONE) # Logs are easier to read without wrapping

        # Insert the log text
        buffer = text_view.get_buffer()
        buffer.set_text(self.error_log or "No log data available.")

        scrolled.set_child(text_view)
        log_window.set_child(scrolled)
        log_window.present()

    def on_smart_toggle(self, target_type):
        """Toggle streams using cached data with a fallback check."""
        listbox = self.get_parent()
        selected_rows = [row for row in listbox.get_selected_rows() if isinstance(row, JobRow)]

        # Phase 1: Determine the new state
        any_enabled = False
        for row in selected_rows:
            streams = row.job_data.get("sources", {}).get("streams", [])
            for s in streams:
                # Fallback: if 'type' is missing, we can't toggle safely without re-probing
                # but for now, we just skip it to avoid crashes.
                if s.get("type") == target_type and s.get("active"):
                    any_enabled = True
                    break
            if any_enabled: break

        new_state = not any_enabled
        print(f"Smart Toggle [{target_type}]: Setting active to {new_state}")

        # Phase 2: Apply the state
        for row in selected_rows:
            streams = row.job_data.get("sources", {}).get("streams", [])
            for s in streams:
                if s.get("type") == target_type:
                    s["active"] = new_state
            
            # This triggers the UI refresh (count labels)
            row.update_job_data(row.job_data)

    def on_batch_chg_output_dir(self, action, param):
        # 1. Get the selected jobs from your ListBox
        listbox = self.get_parent()
        selected_rows = [row for row in listbox.get_selected_rows() if isinstance(row, JobRow)]
        if not selected_rows:
            return

        selected_job_data = [row.job_data for row in selected_rows]

        # 2. Create and show the window
        # The callback 'self.refresh_job_list' should update the UI labels 
        # to reflect the new directory
        batch_win = BatchOutputDirWindow(
            parent=self.get_root(), 
            selected_jobs=selected_job_data
        )
        batch_win.present()