import gi
gi.require_version("Gdk", "4.0")
from gi.repository import Gtk

class BatchOutputDirWindow(Gtk.Window):
    def __init__(self, parent, selected_jobs):
        super().__init__(title="Batch Change Output Directory", transient_for=parent, modal=True)
        self.set_default_size(450, -1)
        self.set_resizable(False)

        self.selected_jobs = selected_jobs

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15, margin_top=15, 
                       margin_bottom=15, margin_start=15, margin_end=15)
        self.set_child(vbox)

        job_names = []
        for job in selected_jobs:
            raw_text = job.get("name", "")
            job_names.append(f"• {raw_text}")

        jobs_list_str = "\n".join(job_names)
        count = len(selected_jobs)

        # Instruction Label
        lbl_info = Gtk.Label(xalign=0)
        lbl_info.set_markup(f"Change output directory for <b>{count}</b> selected jobs:\n{jobs_list_str}\n")
        vbox.append(lbl_info)

        # The Path Row (mimicking SettingsWindow style)
        path_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        
        self.entry_path = Gtk.Entry(hexpand=True)
        self.entry_path.set_placeholder_text("Select new output directory...")
        
        # Pre-fill with the first job's directory if available
        if selected_jobs and 'output_dir' in selected_jobs[0]:
            self.entry_path.set_text(selected_jobs[0]['output_dir'])

        btn_browse = Gtk.Button(icon_name="folder-open-symbolic")
        btn_browse.connect("clicked", self.on_browse_clicked)

        path_row.append(self.entry_path)
        path_row.append(btn_browse)
        vbox.append(path_row)

        # Action Buttons
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        btn_box.set_halign(Gtk.Align.END)

        btn_cancel = Gtk.Button(label="Cancel")
        btn_cancel.connect("clicked", lambda x: self.close())

        btn_apply = Gtk.Button(label="Apply to All")
        btn_apply.add_css_class("suggested-action")
        btn_apply.connect("clicked", self.on_apply_clicked)

        btn_box.append(btn_cancel)
        btn_box.append(btn_apply)
        vbox.append(btn_box)

    def on_browse_clicked(self, button):
        native = Gtk.FileChooserNative.new(
            title="Select New Output Directory",
            parent=self,
            action=Gtk.FileChooserAction.SELECT_FOLDER,
            accept_label="_Select Folder",
            cancel_label="_Cancel",
        )
        native.connect("response", self.on_folder_picked)
        native.show()

    def on_folder_picked(self, native, response):
        if response == Gtk.ResponseType.ACCEPT:
            folder = native.get_file()
            self.entry_path.set_text(folder.get_path())
        native.destroy()

    def on_apply_clicked(self, button):
        new_path = self.entry_path.get_text().strip()
        if not new_path:
            return

        # Update the job data
        for job in self.selected_jobs:
            output = job.get("output", {})
            output['directory'] = new_path
            
        self.close()