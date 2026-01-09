import gi
gi.require_version("Gdk", "4.0")
from gi.repository import Gtk, Gio, Gdk
from UI.JobSetupWindow import JobSetupWindow
from UI.Constants import CONTEXT_MENU_XML

class JobRow(Gtk.ListBoxRow):
    def __init__(self, job_id, job_data, _, app):
        super().__init__()
        self.job_id = job_id
        self.job_data = job_data
        self.app = app

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_child(vbox)

        self.label = Gtk.Label(xalign=0)

        # Add a sub-label for source info
        src_count = len(job_data["sources"]["files"])
        strm_count = len(job_data["sources"]["streams"])
        self.lbl_info = Gtk.Label(xalign=0)
        self.lbl_info.set_markup(f"<span size='small' alpha='70%'>{src_count} Files, {strm_count} Streams</span>")

        self.progress_bar = Gtk.ProgressBar(hexpand=True)
        self.progress_bar.set_show_text(True)
        
        vbox.append(self.label)
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

        action_group = Gio.SimpleActionGroup.new()
        
        def add_act(name, callback):
            act = Gio.SimpleAction.new(name, None)
            act.connect("activate", callback)
            action_group.add_action(act)

        add_act("job_setup", self.on_job_setup)
        add_act("remove_job", self.on_remove)
        add_act("batch_tpl_video", lambda a, p: self.on_batch_template("video"))
        add_act("batch_tpl_audio", lambda a, p: self.on_batch_template("audio"))
        add_act("batch_tpl_subtitle", lambda a, p: self.on_batch_template("subtitle"))
        
        self.insert_action_group("context", action_group)

        self.popover = Gtk.PopoverMenu.new_from_model(menu_model)
        self.popover.set_parent(self)
        self.popover.set_has_arrow(False)
    
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

    def update_job_data(self, new_data):
        """Updates the internal data and UI of this specific row"""
        self.job_data = new_data
        title = new_data.get("name") or "Job"
        self.label.set_markup(f"<b>{title}</b>")
        src_count = len(new_data["sources"]["files"])
        strm_count = len(new_data["sources"]["streams"])
        self.lbl_info.set_markup(f"<span size='small' alpha='70%'>{src_count} Files, {strm_count} Streams</span>")

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
        """Opens a picker filtered by the selected stream type"""
        from UI.TemplatePickerWindow import TemplatePickerWindow
        
        # Store target_type for use in the callback
        self._current_batch_type = target_type 

        picker = TemplatePickerWindow(
            parent_window=self.get_root(),
            current_val="",
            stream_type=target_type, # This prevents the NoneType error!
            on_select=self._apply_batch_template_confirmed
        )
        picker.present()

    def _apply_batch_template_confirmed(self, template_name):
        target_type = self._current_batch_type
        listbox = self.get_parent()
        selected_rows = listbox.get_selected_rows()
        
        # We need the parser to know which stream is what type inside the loop
        # Since JobSetupWindow already has logic to get info, we assume 
        # JobRow can access the app's media parser.
        media_parser = self.app.parsers['media']

        for row in selected_rows:
            if isinstance(row, JobRow):
                # Streams are stored by index in YAML. We need to check their real type.
                # Usually, it's safer to check the actual file again or use cached info.
                files = row.job_data["sources"]["files"]
                streams = row.job_data["sources"]["streams"]

                for s_entry in streams:
                    if s_entry.get("active"):
                        # Get real stream info to verify type
                        try:
                            file_path = files[s_entry["file"]]
                            info = media_parser.get_info(file_path)
                            real_stream = info["streams"][s_entry["index"]]
                            
                            if real_stream.get("codec_type") == target_type:
                                s_entry["template"] = template_name
                        except:
                            continue
                
                row.update_job_data(row.job_data)