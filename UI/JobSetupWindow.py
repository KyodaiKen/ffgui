import gi
gi.require_version("Gdk", "4.0")
from gi.repository import Gtk, Gio, Gdk, Pango
from UI.SourceStreamRow import SourceStreamRow
from Core.Utils import format_duration, get_file_title
import av

class JobSetupWindow(Gtk.ApplicationWindow):
    def __init__(self, parent_window, job, **kwargs):
        super().__init__(**kwargs, title="Job Setup")
        self.job = job
        self.source_paths = []
        # Structure: {(file_path, stream_index): {"template": "...", "disposition": "...", "active": True}}
        self.selected_streams = {}
        self.parent_window = parent_window

        # Set window size
        self.set_size_request(640, 480)
        self.set_transient_for(parent_window)
        self.set_modal(True)

        # Create a CSS Provider
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data("""
            /* Target the rows inside the streams list specifically */
            #streams_list row:hover {
                background-color: transparent;
            }
            /* Optional: ensure they don't look 'selected' either since mode is NONE */
            #streams_list row:selected {
                background-color: transparent;
            }
        """, -1)

        # Apply the provider to the display
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        # Main box of our window
        self.grid = Gtk.Grid(orientation=Gtk.Orientation.VERTICAL, vexpand=True, row_spacing=6, column_spacing=6)
        self.grid.props.margin_start = 6
        self.grid.props.margin_end = 6
        self.grid.props.margin_top = 6
        self.grid.props.margin_bottom = 6
        self.set_child(self.grid)

        # Row for Name
        self.lbl_name = Gtk.Label(halign=Gtk.Align.END, valign=Gtk.Align.FILL)
        self.lbl_name.set_text("Name: ")
        self.entry_name = Gtk.Entry(hexpand = True)
        self.grid.attach(self.lbl_name, 0, 0, 1, 1)
        self.grid.attach(self.entry_name, 1, 0, 2, 1)

        # Row for Source List
        self.lbl_srclst = Gtk.Label(halign=Gtk.Align.END, valign=Gtk.Align.START)
        self.lbl_srclst.set_text("Source Files: ")
        self.lst_source_files = Gtk.ListBox(hexpand = True)
        self.lst_source_files.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.lst_source_files.set_activate_on_single_click(False)
        self.scroll_source_files = Gtk.ScrolledWindow()
        self.scroll_source_files.set_child(self.lst_source_files)
        self.scroll_source_files.set_min_content_height(120)
        self.scroll_source_files.set_max_content_height(120)
        self.scroll_source_files.set_propagate_natural_height(True)
        self.grid.attach(self.lbl_srclst, 0, 1, 1, 1)
        self.grid.attach(self.scroll_source_files, 1, 1, 1, 1)
        box_right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.btn_add = Gtk.Button(label = "Add Source File(s)")
        self.btn_rm = Gtk.Button(label = "Remove Selected")
        self.btn_up = Gtk.Button(label = "Move Up")
        self.btn_dwn = Gtk.Button(label = "Move Down")
        self.btn_clear = Gtk.Button(label = "Clear List")
        self.btn_clear.add_css_class("destructive-action")
        box_right.append(self.btn_add)
        box_right.append(self.btn_rm)
        box_right.append(self.btn_up)
        box_right.append(self.btn_dwn)
        box_right.append(self.btn_clear)
        self.btn_add.connect("clicked", self.on_add_clicked)
        self.btn_rm.connect("clicked", self.on_remove_clicked)
        self.btn_up.connect("clicked", self.on_move_up_clicked)
        self.btn_dwn.connect("clicked", self.on_move_down_clicked)
        self.btn_clear.connect("clicked", self.on_remove_all)
        self.grid.attach(box_right, 2, 1, 1, 1)

        # Row for Source Streams
        self.lbl_strmlst = Gtk.Label(halign=Gtk.Align.END, valign=Gtk.Align.START)
        self.lbl_strmlst.set_text("Source Streams: ")
        self.lst_source_streams = Gtk.ListBox(hexpand = True)
        self.lst_source_streams.set_selection_mode(Gtk.SelectionMode.NONE)
        self.lst_source_streams.set_name("streams_list")
        self.scroll_streams = Gtk.ScrolledWindow(vexpand=True)
        self.scroll_streams.set_child(self.lst_source_streams)
        self.scroll_streams.set_size_request(-1, 120)
        self.grid.attach(self.lbl_strmlst, 0, 2, 1, 1)
        self.grid.attach(self.scroll_streams, 1, 2, 2, 1)   

        # Row for Destination Streams
        self.lbl_dest_strmlst = Gtk.Label(halign=Gtk.Align.END, valign=Gtk.Align.START)
        self.lbl_dest_strmlst.set_text("Destination Streams: ")
        self.lst_dest_streams = Gtk.ListBox(hexpand = True)
        self.lst_dest_streams.set_selection_mode(Gtk.SelectionMode.NONE)
        self.lst_dest_streams.set_name("streams_list")
        self.scroll_dest_streams = Gtk.ScrolledWindow()
        self.scroll_dest_streams.set_child(self.lst_dest_streams)
        self.scroll_dest_streams.set_size_request(-1, 140)
        self.grid.attach(self.lbl_dest_strmlst, 0, 3, 1, 1)
        self.grid.attach(self.scroll_dest_streams, 1, 3, 2, 1)   

        self.btn_ok = Gtk.Button(label="OK")
        self.btn_ok.add_css_class("suggested-action")
        self.grid.attach(self.btn_ok, 2, 4, 1, 1)

        # Drag and Drop Logic
        drop_target = Gtk.DropTarget.new(Gdk.FileList, Gdk.DragAction.COPY)
        drop_target.connect("drop", self.on_file_drop)
        self.lst_source_files.add_controller(drop_target)

    def get_stream_description(self, stream):
        # Logic to find a valid name/title
        meta = stream.metadata or {}
        title = meta.get('title') or meta.get('NAME') or meta.get('label')
        
        # Ignore handler-related names that aren't useful labels
        handler_names = ['handler', 'handlername', 'videohandler', 'audiohandler', 'soundhandler']
        handler_val = meta.get('handler_name', '').lower().replace(" ", "")
        
        if not title and handler_val not in handler_names:
            title = meta.get('handler_name')

        title = title+" " if title else ""

        if stream.type == 'video':
                fps = stream.average_rate
                fps_str = ""
                if fps and fps.numerator > 0:
                    if fps.denominator == 1:
                        fps_str = f"{fps.numerator}"
                    else:
                        fps_str = f"{fps.numerator}/{fps.denominator} ({float(fps):.4f})"
                desc = f"{title}(Video) {stream.codec_context.codec.long_name} {stream.profile}, {stream.width}x{stream.height}, {stream.pix_fmt}, {fps_str} FPS"
                sdesc = f"V:{stream.name.upper()}"
            
        elif stream.type == 'audio':
            sr = stream.sample_rate
            fmt = stream.format.name if stream.format else ""
            ch = f"{stream.channels}ch"
            desc = f"{title}(Audio) {stream.codec_context.codec.long_name}, {ch}, {fmt}, {sr} Hz"
            sdesc = f"A:{stream.name.upper()}"
        
        else:
            desc = f"{title}({stream.type}): {stream.codec.long_name}"
            sdesc = f"{stream.name.upper()}"

        return (desc, sdesc)

    def save_stream_state(self):
        """Saves current widget values into the cache using row identity"""
        row = self.lst_source_streams.get_first_child()
        while row:
            if isinstance(row, SourceStreamRow):
                # Use the path stored directly in the row
                key = (row.source_path, row.stream_index)
                
                self.selected_streams[key] = {
                    "active": row.chk.get_active(),
                    "template": row.ent_tpl.get_text(),
                    "disposition": row.ent_dsp.get_text(),
                    "language": row.ent_lng.get_text()
                }
            row = row.get_next_sibling()

    def get_row_at_index(self, index):
        """Safely retrieves the ListBoxRow at a specific index"""
        count = 0
        child = self.lst_source_files.get_first_child()
        while child:
            if count == index:
                return child
            child = child.get_next_sibling()
            count += 1
        return None
    
    def get_sources(self):
        # 1. Save current state of entries before we clear them
        self.save_stream_state()
        self.lst_source_streams.remove_all()

        for source_path in self.source_paths:
            file_title = get_file_title(source_path)
            
            # Open file to get container-level metadata
            try:
                with av.open(source_path) as media:
                    # Calculate and format duration
                    duration_secs = float(media.duration / 1000000) if media.duration else 0
                    duration_str = format_duration(duration_secs)

                    # Create a container box for the header (Title on Left, Duration on Right)
                    header_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
                    header_hbox.set_margin_top(6)
                    header_hbox.set_margin_end(24)
                    header_hbox.set_margin_bottom(3)

                    # Filename Label
                    lbl_file = Gtk.Label(label=f"<big><b>{file_title}</b></big>", 
                                         use_markup=True, xalign=0, hexpand=True)
                    lbl_file.set_ellipsize(Pango.EllipsizeMode.END)
                    header_hbox.append(lbl_file)

                    # Duration Label (Normal size)
                    lbl_dur = Gtk.Label(label=duration_str, xalign=1)
                    header_hbox.append(lbl_dur)

                    header_row = Gtk.ListBoxRow(selectable=False)
                    header_row.set_child(header_hbox)
                    self.lst_source_streams.append(header_row)

                    # Add individual streams for this file
                    for stm_idx, stream in enumerate(media.streams):
                        desc, sdesc = self.get_stream_description(stream)
                        row = SourceStreamRow(desc, source_path, stm_idx, self)
                        
                        # Restore from cache if user had already typed something here
                        key = (source_path, stm_idx)
                        if key in self.selected_streams:
                            data = self.selected_streams[key]
                            row.chk.set_active(data["active"])
                            row.ent_tpl.set_text(data["template"])
                            row.ent_dsp.set_text(data["disposition"])
                            row.ent_lng.set_text(data['language'])
                        else:
                            # Standard default for fresh files
                            if stream.type in ['video', 'audio']:
                                row.chk.set_active(True)
                            
                        self.lst_source_streams.append(row)

            except Exception as e:
                # Handle corrupted files or unsupported formats gracefully in the UI
                error_row = Gtk.ListBoxRow(selectable=False)
                error_label = Gtk.Label(label=f"  Error opening {file_title}: {e}", xalign=0)
                error_label.add_css_class("error") # Assuming you have an error style
                error_row.set_child(error_label)
                self.lst_source_streams.append(error_row)

    def sync_data_model(self):
        """Rebuild the list based on the current UI order"""
        self.source_paths = []
        row = self.lst_source_files.get_first_child()
        while row:
            label = row.get_child()
            # We use the tooltip or a custom attribute to store the REAL path
            full_path = label.get_tooltip_text() 
            self.source_paths.append(full_path)
            row = row.get_next_sibling()
        self.get_sources()

    def add_file_to_list(self, file):
        label = Gtk.Label(label=file.get_path(), tooltip_text=file.get_path())
        label.set_xalign(0.0)
        label.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
        label.set_hexpand(True)
        label.set_width_chars(10)
        self.lst_source_files.append(label)

    def on_file_drop(self, target, value, x, y):
        # 'value' will be a Gdk.FileList object
        files = value.get_files()
        
        for file in files:
            info = file.query_info("standard::type", Gio.FileQueryInfoFlags.NONE, None)
            file_type = info.get_file_type()

            if file_type == Gio.FileType.DIRECTORY:
                continue
            
            # If it's a regular file, add it to your ListBox
            self.add_file_to_list(file)

        self.sync_data_model()
            
        return True # Return True to indicate the drop was handled
    
    def on_add_clicked(self, button):
        dialog = Gtk.FileDialog.new()
        dialog.set_title("Select Source Files")
        dialog.open_multiple(self, None, self.on_add_dialog_finish)

    def on_add_dialog_finish(self, dialog, result):
        try:
            # Retrieve the GListModel of Gio.File objects
            files_list_model = dialog.open_multiple_finish(result)
            
            if files_list_model:
                # Iterate through the returned ListModel
                for i in range(files_list_model.get_n_items()):
                    file = files_list_model.get_item(i)
                    # Use your existing method to update UI and Data Model
                    self.add_file_to_list(file)
                
                self.sync_data_model()
                    
        except Exception as e:
            # This catches if the user cancels the dialog
            print(f"File selection cancelled or failed: {e}")

    def on_move_up_clicked(self, button):
        selected_rows = self.lst_source_files.get_selected_rows()
        if not selected_rows:
            return

        row = selected_rows[0]
        index = row.get_index()

        if index > 0:
            target_index = index - 1
            child_widget = row.get_child()
            row.set_child(None)
            self.lst_source_files.remove(row)
            self.lst_source_files.insert(child_widget, target_index)
            new_row = self.get_row_at_index(target_index)
            if new_row:
                self.lst_source_files.select_row(new_row)
                self.sync_data_model()

    def on_move_down_clicked(self, button):
        selected_rows = self.lst_source_files.get_selected_rows()
        if not selected_rows:
            return

        row = selected_rows[0]
        index = row.get_index()
        total = self.get_total_rows()

        if index < total - 1:
            target_index = index + 1
            
            child_widget = row.get_child()
            
            # Disconnect the child from the row
            row.set_child(None)
            self.lst_source_files.remove(row)
            
            # Re-insert
            self.lst_source_files.insert(child_widget, target_index)
            
            new_row = self.get_row_at_index(target_index)
            if new_row:
                self.lst_source_files.select_row(new_row)
                self.sync_data_model()

    def get_total_rows(self):
        """Counts how many rows are currently in the list"""
        count = 0
        child = self.lst_source_files.get_first_child()
        while child:
            count += 1
            child = child.get_next_sibling()
        return count

    def on_remove_clicked(self, button):
        selected_rows = self.lst_source_files.get_selected_rows()
        for row in selected_rows:
            # In GTK4, widgets remove themselves from their parent
            self.lst_source_files.remove(row)
            row = None
        self.sync_data_model()

    def on_remove_all(self, button):
        self.lst_source_files.remove_all()
        self.sync_data_model()