import gi

from Models.TemplateDataModel import TemplateDataModel
gi.require_version("Gdk", "4.0")
from gi.repository import GLib, Gtk, Gio, Gdk, Pango
from UI.SourceStreamRow import SourceStreamRow
from UI.SinglePickerWindow import SinglePickerWindow
from UI.MetadataManagerWindow import MetadataManagerWindow
from UI.ContainerParameterEditorWindow import ContainerParameterEditorWindow
from Models.JobsDataModel import JobsDataModel
from Core.Utils import seconds_to_time, get_file_title

class JobSetupWindow(Gtk.ApplicationWindow):
    def __init__(self, parent_window, mode="create", job=None, **kwargs):
        super().__init__(**kwargs, title="Job Setup")
        self.is_loading = True

        # 1. Explicitly grab the application instance
        self.app = Gtk.Application.get_default()
        self.on_job_setup_finished = None
        
        # 2. Safety check: Ensure the media parser exists
        if not hasattr(self.app, 'parsers'):
             print("Warning: Media parsers not found on the application instance.")
        self.mode = mode
        self.parent_window = parent_window

        # 1. Initialize data structure from Model
        if mode in ["edit", "clone"] and job:
            self.job_data = job
            if mode == "clone":
                self.job_data["name"] += " (Copy)"
        else:
            self.job_data = JobsDataModel.create_empty_job()

        # --- DATA PREPARATION START ---
        self.source_paths = self.job_data.get("sources", {}).get("files", [])
        self.selected_streams = {}
        self.global_metadata = {}

        # Pre-populate the stream cache from the job data
        # This is critical so get_sources() knows which templates were saved
        for s in self.job_data.get("sources", {}).get("streams", []):
            try:
                # 'file' is the index in the source_paths list
                path = self.source_paths[s["file"]]
                idx = s["index"]
                self.selected_streams[(path, idx)] = s
            except (IndexError, KeyError):
                continue
        # --- DATA PREPARATION END ---

        self.setup_ui()
        
        # 2. Populate UI if we are editing/cloning
        if mode in ["edit", "clone"]:
            # load_job_into_ui calls get_sources, which now sees your populated selected_streams
            self.load_job_into_ui()
            if mode == "clone":
                self.show_clone_warning()
        else:
            self.is_loading = False

    def setup_ui(self):
        """Standard UI Setup (Grid, Lists, Buttons)"""
        # Set window size
        self.set_size_request(640, 480)
        self.set_default_size(1024, 700)
        self.set_transient_for(self.parent_window)
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
        self.entry_name.set_text(self.job_data.get("name", ""))
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
        self.selected_container = self.job_data["output"].get("container", "mkv")

        # 2. Filename Override
        self.entry_output_filename = Gtk.Entry(hexpand=True)
        self.entry_output_filename.set_text(self.job_data["output"].get("filename", ""))
        self.output_subgrid.attach(self.entry_output_filename, 1, 1, 1, 1)

        # 3. Output Directory Picker
        self.output_dir_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self.entry_output_dir = Gtk.Entry(hexpand=True)
        self.entry_output_dir.set_text(self.job_data["output"].get("directory", ""))
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
        self.btn_ok.connect("clicked", self.on_save_job_clicked)
        self.grid.attach(self.btn_ok, 2, 5, 1, 1)

        # Drag and Drop Logic
        drop_target = Gtk.DropTarget.new(Gdk.FileList, Gdk.DragAction.COPY)
        drop_target.connect("drop", self.on_file_drop)
        self.lst_source_files.add_controller(drop_target)

    def load_job_into_ui(self):
        """Maps JobDataModel YAML structure back into UI widgets"""
        self.is_loading = True # Block all automatic syncs
        
        out = self.job_data.get("output", {})
        self.entry_output_dir.set_text(out.get("directory", ""))
        self.entry_output_filename.set_text(out.get("filename", ""))
        self.selected_container = out.get("container", "mkv")

        files = self.job_data.get("sources", {}).get("files", [])
        streams = self.job_data.get("sources", {}).get("streams", [])
        
        # Clear existing state
        self.source_paths = files.copy()
        self.selected_streams = {}

        # 1. Fill Cache directly from YAML
        for s in streams:
            try:
                f_idx = s.get('file')
                if f_idx is not None and 0 <= f_idx < len(self.source_paths):
                    path = self.source_paths[f_idx]
                    # Use the index from YAML, fall back to list order if missing
                    idx = s.get('index', 0) 
                    self.selected_streams[(path, idx)] = s.copy()
            except Exception as e:
                print(f"Error mapping stream: {e}")

        # 2. Rebuild the Top File List UI without triggering sync_data_model
        self.lst_source_files.remove_all()
        for f_path in self.source_paths:
            lbl = Gtk.Label(label=f_path, tooltip_text=f_path)
            lbl.set_xalign(0.0)
            lbl.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
            self.lst_source_files.append(lbl)

        # 3. Now that data is ready, trigger ONE refresh
        self.is_loading = False 
        self.get_sources() 
        self.update_container_ui()

    def show_clone_warning(self):
        """Warns the user they are working on a duplicate"""
        toast = Gtk.Label(label="Cloning Job: Please ensure you change the output filename.")
        toast.add_css_class("warning")
        self.grid.attach(toast, 1, 6, 2, 1)

    def show_error_dialog(self, msg):
        dialog = Gtk.AlertDialog(message="Validation Error", detail=msg)
        dialog.show(self)

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

        self.btn_set_container_params = Gtk.Button(icon_name="view-more-symbolic", tooltip_text="Setup Container Parameters")
        self.btn_set_container_params.connect("clicked", self.on_manage_global_params)
        self.btn_set_container_params.set_has_frame(False)
        tag.append(self.btn_set_container_params)

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
        formats_list = getattr(self.app, 'ffmpeg_data', {}).get('formats', [])

        formats_dict = {}
        for format in formats_list:
            f = format.copy()
            formats_dict[f['name']] = f

        formats_dict['auto'] = {
            "name": "auto",
            "descr": "Let FFMPEG decide which container to use by file extension",
            "aliases": [],
            "is_muxer": True,
            "is_demuxer": False,
            "parameters": [],
            "extensions": []
        }

        formats_list = list(formats_dict.values())
        formats_list.sort(key=lambda x: (x['name'].lower()))

        def is_filter_valid(filter):
            return filter.get("is_muxer", False)

        picker = SinglePickerWindow(
            parent_window = self,
            options = formats_list,
            strings = {
                "title": f"Select a container format",
                "placeholder_text": "Search for a container..."
            },
            item_filter = is_filter_valid,
            on_select = self.apply_container
        )
        picker.present()

    def apply_container(self, new_format):
        self.selected_container = new_format.get('name', "")
        self.update_container_ui()

    def on_manage_global_meta(self, _):
        win = MetadataManagerWindow(self, self.global_metadata, self.save_global_meta)
        win.present()

    def on_manage_global_params(self, _):
        if self.selected_container == "auto":
            return
        win = ContainerParameterEditorWindow(self, self.job_data)
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
    
    def _update_streams_cache(self):
        """Captures the live state from the UI rows into the selected_streams cache."""
        curr = self.lst_source_streams.get_first_child()
        while curr:
            if isinstance(curr, SourceStreamRow):
                # Pull the current configuration from the widget
                config = curr.get_stream_config()
                # Use the path and index as the key so state is tied to the stream, 
                # not the position in the list.
                key = (curr.source_path, curr.stream_index)
                self.selected_streams[key] = config
            curr = curr.get_next_sibling()
    
    def get_sources(self):

        # Save the live state of all current rows into the cache
        self._update_streams_cache()

        # Now clear the list for rebuilding
        self.lst_source_streams.remove_all()

        for source_path in self.source_paths:
            file_title = get_file_title(source_path)
            try:
                media_info = self.app.parsers['media'].get_info(source_path)
                if "error" in media_info: raise Exception(media_info["error"])

                fmt = media_info.get('format', {})

                # Capture the global file duration as a fallback
                file_duration = float(fmt.get('duration', 0))
                duration_str = seconds_to_time(file_duration)

                # File Header
                header_row = self._create_file_header(file_title, duration_str)
                self.lst_source_streams.append(header_row)

                for stm_idx, stream in enumerate(media_info.get('streams', [])):
                    stype = stream.get('codec_type', 'unknown')
                    key = (source_path, stm_idx)
                    
                    # We only look at cached data for the INITIAL bundle
                    cached = self.selected_streams.get(key, {})

                    template_name = cached.get("template", "")
                    transcoding_settings = cached.get("transcoding_settings", {})

                    if not cached:
                        # Determine the target template name, e.g., "Copy Video"
                        target_tpl_name = f"Copy {stype.capitalize()}"
                        tpl_obj = TemplateDataModel.get_template_by_name(self.app, target_tpl_name)
                        
                        if tpl_obj:
                            template_name = target_tpl_name
                            # Pre-populate the bundle with the template's actual settings
                            transcoding_settings = {
                                "codec": tpl_obj.get("codec", "copy"),
                                "parameters": tpl_obj.get("parameters", {}).get("options", {}),
                                "filters": tpl_obj.get("filters", {"mode": "simple", "entries": []})
                            }
                        else:
                            # Fallback if the "Copy" template doesn't exist in the library
                            transcoding_settings = {"codec": "copy"}

                    stream_bundle = {
                        "path": source_path,
                        "index": stm_idx,
                        "type": stype,
                        "description": self.get_stream_description(stream),
                        "duration": stream.get("duration") or file_duration or "0",
                        "active": cached.get("active", stype in ['video', 'audio']),
                        "template": template_name,
                        "transcoding_settings": transcoding_settings,
                        "metadata": cached.get("metadata", {}),
                        "disposition": cached.get("disposition", []),
                        "language": cached.get("language", ""),
                        "trim_start": cached.get("trim_start", ""),
                        "trim_length": cached.get("trim_length", ""),
                        "trim_end": cached.get("trim_end", ""),
                        "stream_delay": cached.get("stream_delay", "0")
                    }

                    row = SourceStreamRow(self, stream_bundle)
                    self.lst_source_streams.append(row)

            except Exception as e:
                self._add_error_row(file_title, e)

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
        """Updates the internal path list from the UI order."""
        new_paths = []
        row = self.lst_source_files.get_first_child()
        while row:
            label = row.get_child()
            full_path = label.get_tooltip_text() 
            if full_path:
                new_paths.append(full_path)
            row = row.get_next_sibling()
        
        self.source_paths = new_paths

        # Only trigger the heavy UI rebuild if we aren't mid-initialization
        if not self.is_loading:
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

        self.is_loading = False
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

    def _create_file_header(self, title, duration):
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        hbox.set_margin_top(6)
        hbox.set_margin_bottom(2)
        hbox.set_margin_end(24)
        lbl = Gtk.Label(label=f"<big><b>{title}</b></big>", use_markup=True, xalign=0, hexpand=True)
        hbox.append(lbl)
        hbox.append(Gtk.Label(label=duration, xalign=1))
        row = Gtk.ListBoxRow(selectable=False)
        row.set_child(hbox)
        GLib.idle_add(self.do_scroll_to_row, row)
        return row

    def on_save_job_clicked(self, _):
        """Gathers UI data DIRECTLY from widgets and saves to JobRow format"""
        final_data = JobsDataModel.create_empty_job()
        final_data["name"] = self.entry_name.get_text()
        final_data["output"]["directory"] = self.entry_output_dir.get_text()
        final_data["output"]["filename"] = self.entry_output_filename.get_text()
        final_data["output"]["container"] = self.selected_container
        final_data["output"]["container_parameters"] = self.job_data["output"].get("container_parameters", [])
        final_data["sources"]["files"] = self.source_paths

        final_streams = []
        max_job_duration = 0.0
        
        # 1. Iterate through the actual ListBox items
        curr = self.lst_source_streams.get_first_child()
        while curr:
            # 2. Only pull data from actual Stream Rows (skipping file headers)
            if isinstance(curr, SourceStreamRow):
                # 3. Pull the LIVE config from the row widget
                stream_cfg = curr.get_stream_config()
                
                try:
                    # Map back to the file index for the Runner
                    f_idx = self.source_paths.index(curr.source_path)
                    stream_cfg["file"] = f_idx
                    
                    # Cleanup template placeholder
                    if stream_cfg.get("template") == "Manual / Custom Settings":
                        stream_cfg["template"] = ""

                    # --- DURATION CALCULATION START ---
                    if stream_cfg.get("active"):
                        # Get original stream duration (from the row's internal data)
                        orig_duration = float(curr.stream_bundle.get("duration") or 0)
                        
                        # Get trim values (assuming they are stored as time strings or seconds)
                        # We use Core.Utils.time_to_seconds if they are strings
                        from Core.Utils import time_to_seconds
                        
                        t_start = time_to_seconds(stream_cfg.get("trim_start") or "0")
                        t_len = time_to_seconds(stream_cfg.get("trim_length") or "0")
                        
                        if t_len > 0:
                            # User explicitly set a length
                            eff_duration = t_len
                        else:
                            # Duration is the remainder of the file after the start trim
                            eff_duration = max(0, orig_duration - t_start)
                        
                        if eff_duration > max_job_duration:
                            max_job_duration = eff_duration
                    # --- DURATION CALCULATION END ---
                    
                    final_streams.append(stream_cfg)
                except ValueError:
                    pass
            curr = curr.get_next_sibling()

        final_data["sources"]["streams"] = final_streams

        if max_job_duration == 0 and self.job_data.get("total_duration"):
            final_data["total_duration"] = self.job_data["total_duration"]
            print("Note: UI calculated 0 duration, preserving existing job duration.")
        else:
            final_data["total_duration"] = max_job_duration

        # 4. Final Validation & Save
        valid, errs = JobsDataModel.validate_job_data(self.app, final_data)
        if not valid:
            self.show_error_dialog("\n".join(errs))
            return

        if self.on_job_setup_finished:
            self.on_job_setup_finished(final_data)

        self.destroy()