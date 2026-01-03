import gi
gi.require_version("Gdk", "4.0")
from gi.repository import Gtk, Gio, Gdk
from Core.Job import Job
from UI.JobRow import JobRow

class MainWindow(Gtk.ApplicationWindow):
    MENU_XML = """
    <?xml version='1.0' encoding='UTF-8'?>
    <interface>
        <menu id='app-menu'>
            <section>
                <item>
                    <attribute name='label'>Open Job List</attribute>
                    <attribute name='action'>win.open_joblist</attribute>
                </item>
                <item>
                    <attribute name='label'>Save Job List</attribute>
                    <attribute name='action'>win.save_joblist</attribute>
                </item>
                <item>
                    <attribute name='label'>Clear Job List</attribute>
                    <attribute name='action'>win.clear_joblist</attribute>
                </item>
            </section>
            <section>
                <item>
                    <attribute name='label'>New job</attribute>
                    <attribute name='action'>win.create_job</attribute>
                </item>
                <item>
                    <attribute name='label'>Create jobs from a directory of files</attribute>
                    <attribute name='action'>win.create_jobs_from_dir</attribute>
                </item>
            </section>
            <section>
                <item>
                    <attribute name='label'>Preferences</attribute>
                    <attribute name='action'>win.pref</attribute>
                </item>
            </section>
            <section>
                <item>
                    <attribute name='label'>About</attribute>
                    <attribute name='action'>win.about</attribute>
                </item>
                <item>
                    <attribute name='label'>Quit</attribute>
                    <attribute name='action'>win.quit</attribute>
                </item>
            </section>
        </menu>
    </interface>
    """

    CONTEXT_MENU_XML = """
    <?xml version='1.0' encoding='UTF-8'?>
    <interface>
        <menu id='context-menu'>
            <section>
                <item>
                    <attribute name='label'>Setup Job...</attribute>
                    <attribute name='action'>context.job_setup</attribute>
                </item>
                <item>
                    <attribute name='label'>Remove Job</attribute>
                    <attribute name='action'>context.remove_job</attribute>
                </item>
            </section>
        </menu>
    </interface>
    """

    def __init__(self, **kargs):
        super().__init__(**kargs, title="ffGUI")
        self.app = self.get_application()
        self.set_size_request(640,480)

        header_bar = Gtk.HeaderBar()
        self.set_titlebar(header_bar)

        builder = Gtk.Builder.new_from_string(self.MENU_XML, -1)
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
            ("about", self.on_about),
            ("quit", self.on_quit)
        ]

        for name, callback in actions:
            action = Gio.SimpleAction.new(name, None)
            action.connect("activate", callback)
            self.add_action(action)

        # List box
        self.listbox = Gtk.ListBox(vexpand=True)
        self.listbox.set_selection_mode(Gtk.SelectionMode.MULTIPLE)
        self.listbox.set_activate_on_single_click(False)
        box_outer.append(self.listbox)

        self.drag_gesture = Gtk.GestureDrag.new()
        self.drag_gesture.set_propagation_phase(Gtk.PropagationPhase.BUBBLE)
        #self.drag_gesture.connect("drag-begin", self.on_drag_begin)
        self.drag_gesture.connect("drag-update", self.on_drag_update)
        #self.drag_gesture.connect("drag-end", self.on_drag_end)
        self.listbox.add_controller(self.drag_gesture)
    
        builder = Gtk.Builder.new_from_string(self.CONTEXT_MENU_XML, -1)
        self.context_menu_model = builder.get_object("context-menu")

        # Add dummy entries for testing
        # dummy_list = [
        #     (1, "Fun.mp4", 0.375, "37.50%, 3000/8000 frames, 500 FPS, ETA 6s"),
        #     (2, "Scary Movie 2.mp4", 0.5, "50.00%, 2355/4711 frames, 480 FPS, ETA 5s"),
        #     (3, "The Song.flac", 0.25, "25.00%, 2m 0s / 4m 0s, 100x, ETA <1s"),
        #     (4, "My Shoes.flac", 0.25, "25.00%, 2m 0s / 4m 0s, 100x, ETA <1s")
        # ]

        # app = self.get_application()

        # for job_id, title, progress, progress_text in dummy_list:
        #     row = self.JobRow(job_id, title, context_menu_model, app)
        #     row.set_progress(progress, progress_text)
        #     self.listbox.append(row)
        #     app.Jobs[job_id] = Job(title, title)

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
        pass

    def on_save_joblist(self, action, param):
        pass

    def on_clear_joblist(self, action, param):
        pass

    def on_create_job(self, action, param):
        def on_open_response(dialog, result, data=None):
            #try:
            # 'open_finish' returns a Gio.File object
            file = dialog.open_finish(result)
            if file is not None:
                # .get_path() returns the absolute system path as a string
                file_path = file.get_path()
                file_name = file.get_basename()

                print(f"User selected: {file_path}")

                # Create job
                job = Job(file_name, file_path)
                job_id = len(self.app.Jobs) + 1
                self.app.Jobs[job_id] = job

                # Add job to list box
                row = JobRow(job_id, file_name, job, self.context_menu_model, self.app)
                self.listbox.append(row)
            else:
                print("No file was selected.")
                    
            #except Exception as e:
            #    print(f"Dialog closed or error occurred: {e}")

        dialog = Gtk.FileDialog.new()
        dialog.set_title("Open Media File")
        dialog.open(None, None, on_open_response)

    def on_create_jobs_from_dir(self, action, param):
        pass

    def on_pref(self, action, param):
        pass

    def on_about(self, action, param):
        about_dialog = Gtk.AboutDialog(transient_for=self, modal=True)
        about_dialog.present()

    def on_quit(self, action, param):
        if self.app:
            self.app.quit()