import gi
gi.require_version("Gdk", "4.0")
from gi.repository import Gtk, Gio, Gdk
from UI.JobSetupWindow import JobSetupWindow

class JobRow(Gtk.ListBoxRow):
    def __init__(self, job_id, title, job, menu_model, app):
        super().__init__()
        self.job_id = job_id
        self.job_title = title
        self.job = job
        self.app = app

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_child(vbox)

        self.label = Gtk.Label(xalign=0)

        self.label.set_markup(f"<big>{title}</big>")
        self.progress_bar = Gtk.ProgressBar(hexpand=True)
        self.progress_bar.set_show_text(True)
        self.label.set_can_target(False)
        self.progress_bar.set_can_target(False)
        vbox.append(self.label)
        vbox.append(self.progress_bar)

        action_group = Gio.SimpleActionGroup.new()
                
        actions = [
            ("job_setup", self.on_job_setup),
            ("remove_job", self.on_remove)
        ]

        for name, callback in actions:
            action = Gio.SimpleAction.new(name, None)
            action.connect("activate", callback)
            action_group.add_action(action)

        self.insert_action_group("context", action_group)

        self.popover = Gtk.PopoverMenu.new_from_model(menu_model)
        self.popover.set_parent(self)
        self.popover.set_has_arrow(False)

        gesture = Gtk.GestureClick.new()
        gesture.set_button(3)
        gesture.connect("pressed", self.on_right_click)
        self.add_controller(gesture)

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
        #ids = self.get_selected_job_ids()
        #print(f"Source clicked for Job IDs: {ids}")
        if self.app and self.job:
            self.app.wndJobSetupWindow = JobSetupWindow(self.job, application=self.app)
            self.app.wndJobSetupWindow.present()

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