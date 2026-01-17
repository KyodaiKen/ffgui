import gi
from UI.Builder import Builder
gi.require_version("Gdk", "4.0")
from gi.repository import Gtk, Pango
from UI.MetadataManagerWindow import MetadataManagerWindow
from UI.FlagsPickerWindow import FlagsPickerWindow
from UI.LanguagePickerWindow import LanguagePickerWindow
from UI.TemplateManagerWindow import TemplateManagerWindow
from UI.TemplateEditorWindow import TemplateEditorWindow
from Core.Utils import seconds_to_time, time_to_seconds

class SourceStreamRow(Gtk.ListBoxRow):
    def __init__(self, parent_window, stream_settings=None):
        super().__init__()
        self.parent_window = parent_window
        self.stream_bundle = stream_settings or {}
        data = stream_settings or {}
        self.current_template = data.get("template", "")

        # Data extraction from the new nested anatomy
        self.source_path = data.get("path", "")
        self.stream_index = data.get("index", 0)
        self.stream_type = data.get("type", "unknown")
        self.stream_descr = data.get("description", "")
        
        transcoding_settings = data.get("transcoding_settings", {})
        self.selected_codec_name = transcoding_settings.get("codec") or "copy"
        self.stream_parameters = transcoding_settings.get("parameters", {})
        self.stream_filters = transcoding_settings.get("filters", {"mode": "simple", "entries": []})

        self.current_template = data.get("template", "")
        self.stream_metadata = data.get("metadata", {})
        self.stream_disposition = data.get("disposition", [])
        
        raw_duration = data.get("duration", 0)
        if isinstance(raw_duration, str) and ":" in raw_duration:
            self.total_duration = time_to_seconds(raw_duration)
        else:
            self.total_duration = float(raw_duration or 0)

        # UI Setup
        self._start_modified_once = False
        self._is_calculating = False

        grid = Gtk.Grid(orientation=Gtk.Orientation.VERTICAL, row_spacing=6, column_spacing=6)
        grid.set_hexpand(True)
        self.set_child(grid)

        # Row 0: Checkbox, Label, Metadata
        self.chk = Gtk.CheckButton()
        self.chk.set_active(data.get("active", True))
        grid.attach(self.chk, 0, 0, 1, 1)

        self.lbl_strm = Gtk.Label(xalign=0, label=f"<b>{self.stream_descr}</b>", use_markup=True)
        self.lbl_strm.set_ellipsize(Pango.EllipsizeMode.END)
        grid.attach(self.lbl_strm, 1, 0, 2, 1)

        self.btn_meta = Gtk.Button(icon_name="tag-symbolic", halign=Gtk.Align.END)
        self.btn_meta.set_margin_end(24)
        grid.attach(self.btn_meta, 3, 0, 1, 1) 
        self.btn_meta.connect("clicked", self.on_manage_meta)

        # Row 1: Template & Language
        self.tpl_lng_subgrid = Gtk.Grid(column_spacing=4, row_spacing=4, hexpand=True)
        grid.attach(self.tpl_lng_subgrid, 1, 1, 3, 1)

        self.tpl_lng_subgrid.attach(Gtk.Label(xalign=0, label="Encoding Source"), 0, 0, 2, 1)
        self.ent_tpl = Gtk.Entry(hexpand=True, editable=False, can_focus=False)
        self.tpl_lng_subgrid.attach(self.ent_tpl, 0, 1, 1, 1)

        action_group = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        action_group.add_css_class("linked")
        self.tpl_lng_subgrid.attach(action_group, 1, 1, 1, 1)

        self.btn_srch = Gtk.Button(icon_name="search-symbolic")
        self.btn_srch.connect("clicked", self.on_search_tpl_click)
        action_group.append(self.btn_srch)

        self.btn_settings = Gtk.Button(icon_name="emblem-system-symbolic")
        self.btn_settings.connect("clicked", self.on_edit_settings_click)
        action_group.append(self.btn_settings)

        self.ent_lng = Gtk.Entry(width_chars=3)
        self.ent_lng.set_text(data.get("language", ""))
        self.tpl_lng_subgrid.attach(self.ent_lng, 2, 1, 1, 1)

        self.btn_srch_lng = Gtk.Button(icon_name="search-symbolic", halign=Gtk.Align.END)
        self.btn_srch_lng.set_margin_end(24)
        self.btn_srch_lng.connect("clicked", self.on_search_lng_click)
        self.tpl_lng_subgrid.attach(self.btn_srch_lng, 3, 1, 1, 1)

        # Row 2: Disposition
        grid.attach(Gtk.Label(halign=Gtk.Align.END, label="Disposition:"), 1, 2, 1, 1)
        self.dispositions = self.create_disposition_pills(self.stream_disposition)
        grid.attach(self.dispositions, 2, 2, 1, 1)

        self.btn_add_dsp = Gtk.Button(icon_name="search-symbolic", halign=Gtk.Align.END)
        self.btn_add_dsp.set_margin_end(24)
        self.btn_add_dsp.connect("clicked", self.on_add_dsp_click)
        grid.attach(self.btn_add_dsp, 3, 2, 1, 1)

        # Row 3: Trim & Delay
        self.tpl_trim = Gtk.Grid(column_spacing=12, row_spacing=4, hexpand=True)
        grid.attach(self.tpl_trim, 1, 3, 3, 1)

        for i, lbl in enumerate(["Trim Start", "Trim Length", "Trim End", "Delay (ms)"]):
            self.tpl_trim.attach(Gtk.Label(xalign=0, label=lbl), i, 2, 1, 1)

        self.ent_tstart = Gtk.Entry(hexpand=True, text=data.get("trim_start", ""))
        self.ent_tlen = Gtk.Entry(hexpand=True, text=data.get("trim_length", ""))
        self.ent_tend = Gtk.Entry(hexpand=True, text=data.get("trim_end", ""))
        self.ent_sdly = Gtk.Entry(hexpand=True, text=str(data.get("stream_delay", "0")))
        self.ent_sdly.set_margin_end(24)
        
        for i, entry in enumerate([self.ent_tstart, self.ent_tlen, self.ent_tend, self.ent_sdly]):
            self.tpl_trim.attach(entry, i, 3, 1, 1)

        # Connections
        self.ent_tstart.connect("changed", self.on_trim_time_changed)
        self.ent_tlen.connect("changed", self.on_trim_len_changed)
        self.ent_tend.connect("changed", self.on_trim_end_changed)

        self.ent_tpl.set_text(self.current_template or "")
        
        self.refresh_template_ui()
        self.update_meta_button_style()

    def get_stream_config(self):
        """Returns the nested configuration directly from the UI state."""
        # Pull current state from local variables/widgets
        codec = getattr(self, 'custom_codec', self.selected_codec_name) or "copy"
        settings = getattr(self, 'custom_settings', self.stream_parameters)
        filters = getattr(self, 'custom_filters', self.stream_filters)

        return {
            "active": self.chk.get_active(),
            "index": self.stream_index,
            "type": self.stream_type,
            "template": self.ent_tpl.get_text(),
            # THE NESTED ANATOMY
            "transcoding_settings": {
                "codec": codec,
                "parameters": settings,
                "filters": filters
            },
            "language": self.ent_lng.get_text(),
            "disposition": self.stream_disposition,
            "metadata": self.stream_metadata,
            "trim_start": self.ent_tstart.get_text().strip(),
            "trim_length": self.ent_tlen.get_text().strip(),
            "trim_end": self.ent_tend.get_text().strip(),
            "stream_delay": self.ent_sdly.get_text().strip()
        }

    def apply_template(self, template_name):
        from Models.TemplateDataModel import TemplateDataModel
        self.current_template = template_name
        template_obj = TemplateDataModel.get_template_by_name(self.parent_window.app, template_name)
        if template_obj:
            self.selected_codec_name = template_obj.get("codec", self.selected_codec_name)
            self.stream_parameters = template_obj.get("parameters", {}).get("options", {})
            self.stream_filters = template_obj.get("filters", {"mode": "simple", "entries": []})
            for attr in ['custom_codec', 'custom_settings', 'custom_filters']:
                if hasattr(self, attr): delattr(self, attr)
        self.refresh_template_ui()

    # (Metadata, Language, and Disposition logic exactly as provided in your prompt)
    def create_disposition_pills(self, disposition_str):
        self.dispositions = Gtk.FlowBox(orientation=Gtk.Orientation.HORIZONTAL, selection_mode=Gtk.SelectionMode.NONE, 
                                        column_spacing=6, row_spacing=6, halign=Gtk.Align.START, hexpand=True)
        self.dispositions.set_margin_start(0)
        self.dispositions.set_margin_end(0)
        self.dispositions.set_margin_top(0)
        self.dispositions.set_margin_bottom(0)
        Builder.build_pill(self.dispositions, disposition_str)
        return self.dispositions

    def refresh_template_ui(self):
        if self.current_template:
            self.ent_tpl.set_text(self.current_template)
            self.ent_tpl.remove_css_class("warning")
        else:
            self.ent_tpl.set_text("Manual / Custom Settings")
            self.ent_tpl.add_css_class("warning")

    def on_trim_time_changed(self, _):
        if self._is_calculating: return
        if not self._start_modified_once:
            current_length_val = time_to_seconds(self.ent_tlen.get_text())
            current_end_val = time_to_seconds(self.ent_tend.get_text())
            if current_end_val == 0 and current_length_val > 0:
                self._is_calculating = True
                start_sec = time_to_seconds(self.ent_tstart.get_text())
                self.ent_tend.set_text(seconds_to_time(self.total_duration))
                self.ent_tlen.set_text(seconds_to_time(max(0, self.total_duration - start_sec)))
                self._is_calculating = False
                self._start_modified_once = True
                return 
        self._sync_len_from_start_and_end()

    def _sync_len_from_start_and_end(self):
        if self._is_calculating: return
        self._is_calculating = True
        s, e = time_to_seconds(self.ent_tstart.get_text()), time_to_seconds(self.ent_tend.get_text())
        if e > 0:
            self.ent_tlen.set_text(seconds_to_time(max(0, e - s)))
        self._is_calculating = False

    def on_trim_len_changed(self, _):
        if self._is_calculating: return
        self._is_calculating = True
        s, l = time_to_seconds(self.ent_tstart.get_text()), time_to_seconds(self.ent_tlen.get_text())
        if l > 0:
            self.ent_tend.set_text(seconds_to_time(s + l))
        self._is_calculating = False

    def on_trim_end_changed(self, _):
        if self._is_calculating: return
        self._sync_len_from_start_and_end()

    def on_edit_settings_click(self, _):
        # 1. Prepare the nested data bundle for the Editor
        # We ensure 'parameters' are wrapped in 'options' as expected by TemplateEditorWindow
        current_data = {
            "type": self.stream_type,
            "transcoding_settings": {
                "codec": getattr(self, 'custom_codec', self.selected_codec_name),
                "parameters": getattr(self, 'custom_settings', self.stream_parameters),
                "filters": getattr(self, 'custom_filters', self.stream_filters)
            }
        }

        def on_custom_settings_saved(new_data):
            """
            Callback from TemplateEditorWindow.
            new_data arrives in a structure where parameters are already extracted.
            """
            # Update ephemeral custom state
            self.custom_codec = new_data.get("codec")
            # Note: TemplateEditorWindow returns parameters as a flat dict in ephemeral mode
            self.custom_settings = new_data.get("parameters", {})
            self.custom_filters = new_data.get("filters", {"mode": "simple", "entries": []})

            # Immediately update the 'active' settings to reflect the change
            self.selected_codec_name = self.custom_codec
            self.stream_parameters = self.custom_settings
            self.stream_filters = self.custom_filters

            # Reset template name to empty string (Manual mode)
            self.current_template = "" 
            self.refresh_template_ui()
            self.update_meta_button_style()

        # The 'template' argument here is actually our 'current_data' bundle
        win = TemplateEditorWindow(
            parent_window=self.parent_window,
            template=current_data,
            on_save_callback=on_custom_settings_saved,
            is_ephemeral=True 
        )
        win.present()

    def on_manage_meta(self, _):
        win = MetadataManagerWindow(self.parent_window, self.stream_metadata, self.save_meta)
        win.present()

    def save_meta(self, meta):
        self.stream_metadata = meta
        self.update_meta_button_style()

    def update_meta_button_style(self):
        if self.stream_metadata: self.btn_meta.add_css_class("suggested-action")
        else: self.btn_meta.remove_css_class("suggested-action")

    def on_add_dsp_click(self, button):
        opts = getattr(self.parent_window.app, 'ffmpeg_data', {}).get('dispositions', {}).get('options', [])
        self.pw = FlagsPickerWindow(parent=self.parent_window, options=opts, current_values=self.stream_disposition, on_apply=self.apply_disposition)
        self.pw.present()

    def apply_disposition(self, selected_flags):
        self.stream_disposition = selected_flags
        while child := self.dispositions.get_first_child(): self.dispositions.remove(child)
        Builder.build_pill(self.dispositions, self.stream_disposition)

    def on_search_tpl_click(self, button):
        self.pw = TemplateManagerWindow(self.parent_window, picker_mode=True, stream_type=self.stream_type, on_select=self.apply_template)
        self.pw.present()

    def on_search_lng_click(self, button):
        self.pw = LanguagePickerWindow(self.parent_window, current_val=self.ent_lng.get_text(), on_select=self.apply_language)
        self.pw.present()

    def apply_language(self, selected_code): self.ent_lng.set_text(selected_code)