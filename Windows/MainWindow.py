import gi
gi.require_version("Gdk", "4.0")
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gio, Gdk

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
                    <attribute name='label'>Action</attribute>
                    <attribute name='action'>context.action</attribute>
                </item>
                <item>
                    <attribute name='label'>Select source</attribute>
                    <attribute name='action'>context.sel_src</attribute>
                </item>
                <item>
                    <attribute name='label'>Select destination</attribute>
                    <attribute name='action'>context.sel_dst</attribute>
                </item>
                <item>
                    <attribute name='label'>Remove job</attribute>
                    <attribute name='action'>context.remove_job</attribute>
                </item>
            </section>
        </menu>
    </interface>
    """

    class JobRow(Gtk.ListBoxRow):
        def __init__(self, job_id, title, menu_model):
            super().__init__()
            self.job_id = job_id
            self.job_title = title

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
                ("action", self.on_action),
                ("sel_src", self.on_sel_src),
                ("sel_dst", self.on_sel_dst),
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

        def on_action(self, action, param):
            ids = self.get_selected_job_ids()
            print(f"Action clicked for Job IDs: {ids}")

        def on_sel_src(self, action, param):
            ids = self.get_selected_job_ids()
            print(f"Source clicked for Job IDs: {ids}")

        def on_sel_dst(self, action, param):
            ids = self.get_selected_job_ids()
            print(f"Dest clicked for Job IDs: {ids}")

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

    def __init__(self, **kargs):
        super().__init__(**kargs, title="ffGUI")

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
        context_menu_model = builder.get_object("context-menu")

        # Add dummy entries for testing
        dummy_list = [
            (1, "Fun.mp4", 0.375, "37.50%, 3000/8000 frames, 500 FPS, ETA 6s"),
            (2, "Scary Movie 2.mp4", 0.5, "50.00%, 2355/4711 frames, 480 FPS, ETA 5s"),
            (3, "The Song.flac", 0.25, "25.00%, 2m 0s / 4m 0s, 100x, ETA <1s"),
            (4, "My Shoes.flac", 0.25, "25.00%, 2m 0s / 4m 0s, 100x, ETA <1s")
        ]

        for job_id, title, progress, progress_text in dummy_list:
            row = self.JobRow(job_id, title, context_menu_model)
            row.set_progress(progress, progress_text)
            self.listbox.append(row)

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
        pass

    def on_create_jobs_from_dir(self, action, param):
        pass

    def on_pref(self, action, param):
        pass

    def on_about(self, action, param):
        about_dialog = Gtk.AboutDialog(transient_for=self, modal=True)
        about_dialog.present()

    def on_quit(self, action, param):
        app = self.get_application()
        if app:
            app.quit()