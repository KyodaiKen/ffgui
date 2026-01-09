import gi
gi.require_version("Gdk", "4.0")
from gi.repository import GLib, Gtk, Gio, Gdk, Pango
from UI.SourceStreamRow import SourceStreamRow
from UI.ContainerPickerWindow import ContainerPickerWindow
from UI.MetadataManagerWindow import MetadataManagerWindow
from Core.Utils import format_duration, get_file_title
import av

class JobSetupWindow(Gtk.ApplicationWindow):
    def __init__(self, parent_window, job, **kwargs):
        super().__init__(**kwargs, title="Job Setup")
        self.app = self.get_application()
        self.job = job
        self.source_paths = []
        # Structure: {(file_path, stream_index): {"template": "...", "disposition": "...", "active": True}}
        self.selected_streams = {}
        self.global_metadata = {}
        self.parent_window = parent_window

        # Set window size
        self.set_size_request(640, 480)
        self.set_default_size(1024, 700)
        self.set_transient_for(parent_window)
        self.set_modal(True)

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

        # Row 4: Output Configuration Header
        self.lbl_output = Gtk.Label(label="Output Settings: ", halign=Gtk.Align.END, valign=Gtk.Align.START)
        self.lbl_output.set_margin_top(4) # Align with the header text
        self.grid.attach(self.lbl_output, 0, 4, 1, 1)

        # Create a Sub-Grid for grouped output elements
        self.output_subgrid = Gtk.Grid(column_spacing=12, row_spacing=4, hexpand=True)
        self.grid.attach(self.output_subgrid, 1, 4, 2, 1)

        # --- Headers ---
        lbl_head_cont = Gtk.Label(xalign=0)
        lbl_head_cont.set_markup("<b>Container Format</b>")
        
        lbl_head_file = Gtk.Label(xalign=0)
        lbl_head_file.set_markup("<b>Filename</b>")
        
        lbl_head_dir = Gtk.Label(xalign=0)
        lbl_head_dir.set_markup("<b>Output Directory</b>")

        self.output_subgrid.attach(lbl_head_cont, 0, 0, 1, 1)
        self.output_subgrid.attach(lbl_head_file, 1, 0, 1, 1)
        self.output_subgrid.attach(lbl_head_dir, 2, 0, 1, 1)

        # --- Widgets ---

        # 1. Container selection (the Pill)
        self.container_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.output_subgrid.attach(self.container_box, 0, 1, 1, 1)

        # 2. Filename Override
        self.entry_output_filename = Gtk.Entry(hexpand=True)
        self.output_subgrid.attach(self.entry_output_filename, 1, 1, 1, 1)

        # 3. Output Directory Picker
        self.output_dir_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self.entry_output_dir = Gtk.Entry(hexpand=True)
        btn_dir = Gtk.Button(icon_name="folder-open-symbolic")
        btn_dir.connect("clicked", self.on_select_output_dir_clicked)
        
        self.output_dir_box.append(self.entry_output_dir)
        self.output_dir_box.append(btn_dir)
        self.output_subgrid.attach(self.output_dir_box, 2, 1, 1, 1)

        # Initial UI Refresh
        self.selected_container = "auto"
        self.update_container_ui()

        self.btn_ok = Gtk.Button(label="OK")
        self.btn_ok.add_css_class("suggested-action")
        self.grid.attach(self.btn_ok, 2, 5, 1, 1)

        # Drag and Drop Logic
        drop_target = Gtk.DropTarget.new(Gdk.FileList, Gdk.DragAction.COPY)
        drop_target.connect("drop", self.on_file_drop)
        self.lst_source_files.add_controller(drop_target)

    def update_container_ui(self):
        """Refreshes the 'pill' display for the container"""
        while child := self.container_box.get_first_child():
            self.container_box.remove(child)
        
        # Create the pill (similar to DispositionTag but specific for the one choice)
        tag = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        tag.add_css_class("container-tag") 
        
        lbl = Gtk.Label(label=self.selected_container)
        lbl.set_margin_start(8)
        lbl.set_margin_end(8)
        tag.append(lbl)
        
        btn_edit = Gtk.Button(icon_name="search-symbolic", tooltip_text="Search For Container")
        btn_edit.set_has_frame(False)
        btn_edit.connect("clicked", self.on_change_container_clicked)
        tag.append(btn_edit)

        self.btn_global_meta = Gtk.Button(icon_name="tag-symbolic", tooltip_text="Setup Container Metadata")
        self.btn_global_meta.connect("clicked", self.on_manage_global_meta)
        self.btn_global_meta.set_has_frame(False)
        tag.append(self.btn_global_meta)

        # VISUAL FEEDBACK: If metadata exists, highlight the button
        if self.global_metadata:
            self.btn_global_meta.add_css_class("suggested-action") # Or a custom CSS class
            # Optional: Add a badge or change tooltip
            self.btn_global_meta.set_tooltip_text(f"Container Metadata ({len(self.global_metadata)} tags)")
        
        self.container_box.append(tag)

    def on_change_container_clicked(self, btn):
        picker = ContainerPickerWindow(self, self.selected_container, self.apply_container)
        picker.present()

    def apply_container(self, new_format):
        self.selected_container = new_format
        self.update_container_ui()

    def on_manage_global_meta(self, _):
        win = MetadataManagerWindow(self, self.global_metadata, self.save_global_meta)
        win.present()

    def save_global_meta(self, meta):
        self.global_metadata = meta

    def get_stream_description(self, stream):
        """Generates description with decimal FPS and kbps bitrate."""
        meta = stream.get('metadata', {})
        title = meta.get('title') or meta.get('NAME') or ""

        # Consistent bitrate labeling
        bitrate_val = stream.get('bit_rate')
        bitrate_str = f", ~{int(bitrate_val) // 1000} kbps" if bitrate_val else ""

        title_prefix = f"{title} " if title else ""
        codec_long = stream.get('codec_long_name', 'Unknown Codec')
        codec_type = stream.get('codec_type', 'unknown')

        if codec_type == 'video':
            fps_frac = stream.get('frac_avg_frame_rate')
            fps_display = "0"
            if fps_frac:
                fps_decimal = float(fps_frac)
                fps_display = f"{fps_decimal:.3f}".rstrip('0').rstrip('.')
                if fps_frac.denominator != 1:
                    fps_display += f" ({fps_frac.numerator}/{fps_frac.denominator})"

            width = stream.get('width', '?')
            height = stream.get('height', '?')
            pix_fmt = stream.get('pix_fmt', 'unknown')
            return f"{title_prefix}(Video) {codec_long}, {width}x{height}, {pix_fmt}, {fps_display} FPS{bitrate_str}"

        elif codec_type == 'audio':
            sr = stream.get('sample_rate', '?')
            ch = f"{stream.get('channels', '?')}ch"
            return f"{title_prefix}(Audio) {codec_long}, {ch}, {sr} Hz{bitrate_str}"

        return f"{title_prefix}({codec_type}): {codec_long}{bitrate_str}"

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
                    "disposition": row.stream_disposition,
                    "language": row.ent_lng.get_text(),
                    "metadata": row.stream_metadata
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
        self.save_stream_state()
        self.lst_source_streams.remove_all()

        for source_path in self.source_paths:
            file_title = get_file_title(source_path)

            try:
                media_info = self.app.parsers['media'].get_info(source_path)
                if "error" in media_info:
                    raise Exception(media_info["error"])

                fmt = media_info.get('format', {})
                # (Existing bitrate/duration logic...)
                raw_bitrate = fmt.get('bit_rate')
                container_br_str = f"{int(raw_bitrate) // 1000} kbps" if raw_bitrate else ""
                duration_str = format_duration(float(fmt.get('duration', 0)))

                # --- Create Header Row ---
                header_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
                header_hbox.set_margin_top(6)
                header_hbox.set_margin_end(24)
                lbl_file = Gtk.Label(label=f"<big><b>{file_title}</b></big>", use_markup=True, xalign=0, hexpand=True)
                header_hbox.append(lbl_file)
                if container_br_str:
                    header_hbox.append(Gtk.Label(label=container_br_str, xalign=1))
                header_hbox.append(Gtk.Label(label=duration_str, xalign=1))
                
                header_row = Gtk.ListBoxRow(selectable=False)
                header_row.set_child(header_hbox)
                self.lst_source_streams.append(header_row)

                GLib.idle_add(self.do_scroll_to_row, header_row)

                # --- Add individual streams ---
                for stm_idx, stream in enumerate(media_info.get('streams', [])):
                    desc = self.get_stream_description(stream)
                    stype = stream.get('codec_type', 'unknown')
                    
                    # Extract raw stream tags from the file
                    source_stream_tags = dict(stream.get('tags', {}))

                    # Check cache to see if user has already modified this stream
                    key = (source_path, stm_idx)
                    cached_data = self.selected_streams.get(key)
                    
                    # Determine which metadata to use (Cached > Source)
                    initial_meta = cached_data.get("metadata", source_stream_tags) if cached_data else source_stream_tags

                    disposition_obj = stream.get('disposition', {})
                    initial_disposition = self.parse_disposition_to_string(disposition_obj)

                    # Pass this to the row (assuming SourceStreamRow is updated to handle/display it)
                    row = SourceStreamRow(
                        desc, 
                        stype, 
                        source_path, 
                        stm_idx, 
                        self, 
                        initial_metadata=initial_meta,
                        initial_disposition=initial_disposition
                    )

                    if cached_data:
                        row.chk.set_active(cached_data["active"])
                        row.ent_tpl.set_text(cached_data["template"])
                        row.apply_disposition(cached_data["disposition"])
                        row.ent_lng.set_text(cached_data['language'])
                    else:
                        # New stream default: active if V or A
                        if stype in ['video', 'audio']:
                            row.chk.set_active(True)
                        
                        # Set default language from metadata if available
                        lang = source_stream_tags.get('language') or source_stream_tags.get('LANGUAGE', '')
                        row.ent_lng.set_text(lang)

                    row.update_meta_button_style()
                    self.lst_source_streams.append(row)

            except Exception as e:
                # (Existing error handling...)
                error_row = Gtk.ListBoxRow(selectable=False)
                error_row.set_child(Gtk.Label(label=f"  Error parsing {file_title}: {e}", xalign=0))
                self.lst_source_streams.append(error_row)

    def do_scroll_to_row(self, row):
        """Manually scrolls the ScrolledWindow to the position of a specific row"""
        # Get the vertical adjustment of the scrolled window
        adj = self.scroll_streams.get_vadjustment()

        # Find the row's position relative to the ListBox
        # We translate (0,0) of the row into the coordinate space of the ListBox
        _, y = row.translate_coordinates(self.lst_source_streams, 0, 0)

        if y > 0:
            # Set the adjustment value to the row's 'y' coordinate
            # This aligns the top of the row with the top of the scroll area
            adj.set_value(y)

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
        """Adds file to top list and sets initial defaults."""
        label = Gtk.Label(label=file.get_path(), tooltip_text=file.get_path())
        label.set_xalign(0.0)
        label.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
        label.set_hexpand(True)
        label.set_width_chars(10)
        self.lst_source_files.append(label)

        path_str = file.get_path()

        if self.entry_name.get_text() == "":
            self.entry_name.set_text(get_file_title(path_str))
            if self.entry_output_dir.get_text() == "":
                import os
                self.entry_output_dir.set_text(os.path.dirname(path_str))

        # Metadata: Load if we don't have any global metadata yet
        if not self.global_metadata:
            try:
                media_info = self.app.parsers['media'].get_info(path_str)
                format_obj = media_info.get('format', {})
                tags = format_obj.get('tags', {})

                if tags:
                    self.global_metadata = dict(tags)
                    # Force a refresh of the container pill to show the active meta state
                    self.update_container_ui()
                    print(f"Container metadata loaded from: {path_str}")
            except Exception as e:
                print(f"Error retrieving container metadata: {e}")

    def on_file_drop(self, target, value, x, y):
        files = value.get_files()
        for file in files:
            info = file.query_info("standard::type", Gio.FileQueryInfoFlags.NONE, None)
            if info.get_file_type() != Gio.FileType.DIRECTORY:
                self.add_file_to_list(file)

        self.sync_data_model()
        return True
    
    def on_add_clicked(self, button):
        dialog = Gtk.FileDialog.new()
        dialog.set_title("Select Source Files")
        dialog.open_multiple(self, None, self.on_add_dialog_finish)

    def on_add_dialog_finish(self, dialog, result):
        try:
            files_list_model = dialog.open_multiple_finish(result)
            if files_list_model:
                for i in range(files_list_model.get_n_items()):
                    self.add_file_to_list(files_list_model.get_item(i))
                self.sync_data_model()
        except Exception as e:
            print(f"Error selecting files: {e}")

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

    def on_select_output_dir_clicked(self, btn):
        dialog = Gtk.FileDialog.new()
        dialog.set_title("Select Output Directory")
        # Set initial folder if entry has text
        current_path = self.entry_output_dir.get_text()
        if current_path:
            dialog.set_initial_folder(Gio.File.new_for_path(current_path))
            
        dialog.select_folder(self, None, self.on_dir_dialog_finish)

    def on_dir_dialog_finish(self, dialog, result):
        try:
            folder = dialog.select_folder_finish(result)
            if folder:
                self.entry_output_dir.set_text(folder.get_path())
        except Exception as e:
            print(f"Folder selection cancelled: {e}")

    def parse_disposition_to_string(self, disposition_dict):
        """Converts {"default": 1, "dub": 0...} to 'default'"""
        if not disposition_dict:
            return ""
        # Collect keys where value is 1
        active_disps = [k for k, v in disposition_dict.items() if v == 1]
        return ",".join(active_disps)