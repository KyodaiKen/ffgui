import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk
from UI.FlagsPickerWindow import FlagsPickerWindow

class Builder:
    @staticmethod
    def build_pill(flowbox, tags, no_target=False):
        # First, clear existing pills to allow for refreshing
        while child := flowbox.get_first_child():
            flowbox.remove(child)

        if not tags:
            return

        # Handle string or list inputs
        if isinstance(tags, str):
            tags = tags.split(",")
        
        unique_tags = list(dict.fromkeys([t.strip() for t in tags if t.strip()]))

        for tag in unique_tags:
            lbl = Gtk.Label(label=tag)
            lbl.add_css_class("disposition-tag")
            
            # The Magic: If True, the label is invisible to the pointer, 
            # so the click lands on the Button underneath.
            if no_target:
                lbl.set_can_target(False)
                lbl.set_can_focus(False)
                
            flowbox.append(lbl)

    @staticmethod
    def build_value_widget(parent, key, value, schema):
        if not schema:
            print("NO SCHEMA FOR VALUE WIDGET BUILDER!!")
            return Gtk.Entry(text=str(value if value is not None else ""), hexpand=True)

        options_list = schema.get("options", [])
        p_type = str(schema.get("type", "string")).lower()

        # 1. Multi-Select Flags as Pills (Gtk.FlowBox)
        if p_type == "flags" and options_list:
            btn = Gtk.Button(hexpand=True)
            btn.set_valign(Gtk.Align.CENTER)
            
            # The container for the pills inside the button
            flowbox = Gtk.FlowBox(
                selection_mode=Gtk.SelectionMode.NONE,
                column_spacing=4,
                row_spacing=4,
                margin_bottom=0,
                margin_end=0,
                margin_start=0,
                margin_top=0
            )
            btn.set_child(flowbox)

            # Internal helper to refresh the UI
            def refresh_ui(new_value):
                btn._current_value = new_value
                
                Builder.build_pill(flowbox, new_value, no_target=True)
                
                # Show a placeholder if empty
                if not flowbox.get_first_child():
                    lbl = Gtk.Label(label="None selected")
                    lbl.add_css_class("dim-label")
                    flowbox.append(lbl)

            # Initial population
            refresh_ui(value)

            def on_picker_clicked(_):
                strings = {
                    "title": f"Select {key}",
                    "placeholder_text": "Search flags..."
                }
                # Open the window we created earlier
                win = FlagsPickerWindow(
                    parent=parent, 
                    options=options_list, 
                    current_values=btn._current_value, 
                    strings=strings, 
                    on_apply=refresh_ui
                )
                win.present()

            btn.connect("clicked", on_picker_clicked)
            return btn

        # 1. PRIORITY: If there are options, it's a DropDown, regardless of 'type'
        
        if options_list and not p_type == "flags":
            tech_values = [str(o.get('name')) for o in options_list]
            display_names = [f"{o.get('name')} ({o.get('descr')})" if o.get('descr') else str(o.get('name')) for o in options_list]
            
            w = Gtk.DropDown(model=Gtk.StringList.new(display_names), hexpand=True)
            w._tech_values = tech_values
            
            # Determine initial selection
            cur_val = str(value) if value is not None else str(schema.get("default", ""))
            try:
                if cur_val in tech_values:
                    w.set_selected(tech_values.index(cur_val))
            except ValueError:
                pass
            return w

        # 2. NUMERIC: Logic for Spinners
        
        if any(t in p_type for t in ["int", "integer", "float", "double"]):
            # Check if this is a floating point value
            is_float = any(x in p_type for x in ["float", "double"])
            
            v_min = Builder._parse_ffmpeg_num(schema.get("min"), -2147483648)
            v_max = Builder._parse_ffmpeg_num(schema.get("max"), 2147483647)
            
            # Value handling
            if value is None or value == "":
                v_cur = Builder._parse_ffmpeg_num(schema.get("default"), 0)
            else:
                v_cur = Builder._parse_ffmpeg_num(value, 0)

            # Use 0.1 steps for floats, 1.0 for integers
            # step = 0.1 if is_float else 1.0
            step = 1
            adj = Gtk.Adjustment(value=v_cur, lower=v_min, upper=v_max,
                                 step_increment=step, page_increment=step * 10)
            
            w = Gtk.SpinButton(adjustment=adj, numeric=True)
            
            if is_float:
                # CRITICAL: This allows the 22.1 to actually be displayed
                w.set_digits(1) 
            else:
                w.set_digits(0)

            w.set_value(v_cur) 
            return w

        # 3. BOOLEAN
        if p_type in ["bool", "boolean"]:
            active = str(value).lower() in ['true', '1', 'on'] if value is not None else bool(schema.get("default"))
            return Gtk.Switch(active=active, halign=Gtk.Align.START)

        return Gtk.Entry(text=str(value if value is not None else ""), hexpand=True)

    @staticmethod
    def _parse_ffmpeg_num(val, fallback=0):
        """Extracts the first numeric part of a string like '51, 0 means auto'."""
        if isinstance(val, (int, float)):
            return float(val)
        if not val:
            return float(fallback)
        try:
            # Take the first word and strip non-numeric characters
            clean = str(val).split(',')[0].split(' ')[0]
            return float(''.join(c for c in clean if c.isdigit() or c in '.-'))
        except (ValueError, IndexError):
            return float(fallback)