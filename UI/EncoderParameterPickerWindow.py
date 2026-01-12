import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Pango, GLib

class EncoderParameterPickerWindow(Gtk.ApplicationWindow):
    def __init__(self, parent_window, codec_name, stream_type, on_select, **kwargs):
        super().__init__(**kwargs, title=f"Options for {codec_name}")
        self.on_select = on_select
        self.set_default_size(450, 600)
        self.set_transient_for(parent_window)
        self.set_modal(True)

        param_dict = {}
        app = Gtk.Application.get_default()
        ffmpeg_data = getattr(app, 'ffmpeg_data', {})
        
        # 1. Add Global Options
        # We use the context flags (audio/video) to filter, not just group names
        groups = ffmpeg_data.get('globals', [])
        for group in groups:
            group_name = group.get("name", "").lower()
            if group_name in ["av_options", "video", "audio", "subtitle", "common"]:
                for p in group.get("parameters", []):
                    ctx = p.get("context", {})
                    
                    # BITRATE FIX: Check internal context flags. 
                    # 'b' usually has 'video': true AND 'audio': true
                    is_valid = (
                        (stream_type == "video" and ctx.get("video")) or
                        (stream_type == "audio" and ctx.get("audio")) or
                        (stream_type == "subtitle" and ctx.get("subtitle")) or
                        (group_name == "av_options")
                    )

                    if is_valid:
                        name = p.get("name")
                        param_dict[name] = {
                            "name": name,
                            "help": p.get("descr", "Global Option"),
                            "is_global": True,
                            "schema": p
                        }

        # 2. Add Codec-Specific (Private) Options from ffmpeg_data['codecs']
        # We find the codec entry that matches the codec_name provided
        all_codecs = ffmpeg_data.get('codecs', [])
        target_codec = next((c for c in all_codecs if c.get('name') == codec_name), None)
        
        if target_codec:
            codec_params = target_codec.get("parameters", [])
            for p in codec_params:
                name = p.get("name")
                # Private options overwrite Globals of the same name
                param_dict[name] = {
                    "name": name,
                    "help": p.get("descr", "Codec-specific option"),
                    "is_global": False,
                    "schema": p
                }

        self.params = sorted(param_dict.values(), key=lambda x: x['name'])

        # 3. UI Setup
        hb = Gtk.HeaderBar()
        self.set_titlebar(hb)
        self.search_entry = Gtk.SearchEntry(placeholder_text="Filter options (e.g. bitrate, crf)...")
        self.search_entry.connect("search-changed", self.on_search_changed)
        hb.set_title_widget(self.search_entry)

        self.lst_params = Gtk.ListBox()
        self.lst_params.add_css_class("boxed-list")
        self.lst_params.set_filter_func(self.filter_rows)
        self.lst_params.connect("row-activated", self.on_row_activated)

        scroll = Gtk.ScrolledWindow(vexpand=True)
        scroll.set_child(self.lst_params)
        self.set_child(scroll)

        self.create_list_widgets()
        self.search_entry.grab_focus()

    def create_list_widgets(self):
        """Create rows once for maximum performance."""
        for p in self.params:
            row = Gtk.ListBoxRow()
            row._data = p
            row._search_key = f"{p['name']} {p['help']}".lower()

            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4, 
                          margin_start=12, margin_end=12, margin_top=8, margin_bottom=8)
            
            header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            lbl_key = Gtk.Label(xalign=0)
            lbl_key.set_markup(f"<b>{p['name']}</b>")
            
            type_text = "Global" if p['is_global'] else "Private"
            lbl_type = Gtk.Label(xalign=0)
            lbl_type.set_markup(f"<span size='small' alpha='50%'>[{type_text}]</span>")
            
            header.append(lbl_key)
            header.append(lbl_type)
            
            lbl_help = Gtk.Label(label=p['help'], xalign=0, wrap=True)
            lbl_help.add_css_class("caption")

            box.append(header)
            box.append(lbl_help)
            row.set_child(box)
            self.lst_params.append(row)

    def filter_rows(self, row):
        search_text = self.search_entry.get_text().lower()
        if not search_text:
            return True
        return search_text in row._search_key

    def on_search_changed(self, entry):
        self.lst_params.invalidate_filter()

    def on_row_activated(self, listbox, row):
        # Return the parameter name to the callback
        self.on_select(row._data['name'])
        self.destroy()